import ast
import json
import sys
import time
import requests
import telepot
from telepot.delegate import (create_open, pave_event_space,
                              per_callback_query_origin, per_chat_id,include_callback_query_chat_id)
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup


class TelegramBot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(TelegramBot, self).__init__(*args, **kwargs)
        self.stato = "start"
        self.RegStat = 0
        self.keysReg = ["name", "surname",
                        "birth", "gender", "mobile"]
        self.dicReg = {}
        self.info = {"category": ""}

    def check_reg(self, chat_id):
        URL = "http://192.168.1.70:8082/UserReg/CheckReg/"
        response = requests.get(URL + str(chat_id))
        if response:
            return json.loads(response.content)
        else:
            bot.sendMessage(
                chat_id, "Connection failed. Please try again later.")
            return {"category": "FailedConnection"}

    def user_reg(self, chat_id):
        if self.keysReg[self.RegStat] == "birth":
            bot.sendMessage(chat_id, "Insert your birth date (dd-mm-yyyy): ")
        elif self.keysReg[self.RegStat] == "gender":
            bot.sendMessage(chat_id, "What is your gender (m/f/d)?")
        else:
            bot.sendMessage(chat_id, "What's your " +
                            self.keysReg[self.RegStat] + "?")

    def clubsinfo(self, chat_id, club_id):
        URL = "http://192.168.1.70:8080/EndPoints/read_rest/"+club_id
        # Riceve -> {"read_rest":[{"room":nome_stanza,"descriptor":tipo_sensore,"URL":url_sensore},{...,...,...}}
        response = requests.get(URL)
        sensorlinks = json.loads(response.content)
        sensorlinks = sensorlinks["read_rest"]
        SensorsList = ["temperature", "humidity", "presence"]
        message = "These are the club informations: " + '\n'
        for sensor in sensorlinks:
            # Qui controlla che la tupla sensor che contiene (stanza,tipodisensore,URL) sia un sensore della stanza "room1" che e' quella che mostriamo agli utenti, e che sia del tipo di uno della lista SensorList
            if sensor["room"] == "main" and sensor["descriptor"] in SensorsList:
                URL = sensor["URL"]
                try:
                    response = requests.get(URL)
                    response_json = json.loads(response.content)
                    sensorvalue = response_json["e"][0]["v"]
                    sensorunit = response_json["e"][0]["u"]
                    message = message + sensor["descriptor"] + ": " + \
                        str(sensorvalue)[0:4] + " " + sensorunit + "\n"
                except:
                    message = message + \
                        sensor["descriptor"] + ": " + "Unavailable" "\n"
            if sensor["room"] == "main" and sensor["descriptor"] == "photo":
                URLphoto = sensor["URL"]
        #try:
        URL = "http://192.168.1.70:8081/PDE/" + str(club_id)
        response = requests.get(URL)
        response_json = json.loads(response.content)
        message = message + "\n"+"Info about partecipants: " + "\n"
        message = message + "- Gender (male/female/diverse): " + "\n"
        for gender, number in response_json.items():
            message = message +"  " + gender + ":  " + str(number) + "\n"
        #except:
        #    message = message + "Unavailable information"

        try:
            response = requests.get(URLphoto)
            response_json = json.loads(response.content)
            URLphoto = response_json["e"][0]["vs"]
            bot.sendPhoto(chat_id, URLphoto, caption=message)
        except:
            bot.sendMessage(chat_id, message)

    def on_chat_message(self, msg):  # Gestione messaggi in Chat
        content_type, chat_type, chat_id = telepot.glance(msg)
        if self.stato == "start":
            self.info = self.check_reg(chat_id)
            if self.info["category"] == "":
            	self.RegStat = 0
                bot.sendMessage(chat_id, "Hi " + msg["from"]["first_name"] +
                                ", it seems you are not registered. Please insert your data.")
                self.stato = "registration"
                self.user_reg(chat_id)
            else:
                self.stato = "checked"
                self.user_int(msg)
        elif self.stato == "registration":
            self.dicReg[self.keysReg[self.RegStat]] = msg["text"]
            self.RegStat += 1
            if self.RegStat < len(self.keysReg):
                self.user_reg(chat_id)
            else:
                self.stato = "start"
                self.dicReg["chat_id"] = chat_id
                self.dicReg["category"] = "participant"
                URL = "http://192.168.1.70:8082/UserReg/Reg/"
                response = requests.post(URL, json=json.dumps(self.dicReg))
                bot.sendMessage(
                    chat_id, "Thank you " + msg["from"]["first_name"] + ", you are now registered to IoTonight!")
        else:
            self.user_int(msg)

    def user_int(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="List of clubs",
                                         callback_data="ClubsList"),
                    InlineKeyboardButton(
                        text="Help", callback_data="help"),
                ],
            ]
        )

        bot.sendMessage(chat_id, "Hi " + msg["from"]["first_name"] + " choose an option:",
                        reply_markup=keyboard)

    def on_callback_query(self, msg):  # Gestione dei pulsanti
        query_id, chat_id, query_data = telepot.glance(
            msg, flavor="callback_query")
        # quando la sessione scade rifacciamo il controllo dell'utente
        if self.info["category"] == "":
            self.info = self.check_reg(chat_id)
        if self.info["category"] != "":
            if query_data == "ClubsList":
                URL = "http://192.168.1.70:8080/ClubList"
                response = requests.get(URL)
                clubs = json.loads(response.content)
                clubs = clubs["ClubList"]
                buttons = []
                for club in clubs:
                    buttons.append(InlineKeyboardButton(
                        text=club[1], callback_data=club[0]))  # 1=Nome_club, 2=Club_id
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[buttons]
                )
                bot.sendMessage(
                    chat_id, "Choose your favorite clubs:", reply_markup=keyboard
                )
            elif query_data == "help":
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="List of clubs", callback_data="ClubsList"
                            ),
                        ],
                    ]
                )
                bot.sendMessage(
                    chat_id,
                    msg["from"]["first_name"] +
                    ", I am IoTonight bot." + "\n" +
                    "I can send you information about your favorite clubs." + "\n" +
                    "By clicking on the button below you can find the list of currently available clubs, and for each of them you will be able to know the main info about the atmosphere of the event! ",
                    reply_markup=keyboard,
                )
            else:
                # serve ad avere le info del locale una volta schiacciato il pulsante
                self.clubsinfo(chat_id, query_data)


if __name__ == "__main__":

    TOKEN = "947705193:AAHmoKcqM7jcpiR7Y-O30UIliYPjqYaAFwg"
    bot = telepot.DelegatorBot(TOKEN, [
        include_callback_query_chat_id(
            pave_event_space())(
            per_chat_id(), create_open, TelegramBot, timeout=200),
    ])
    MessageLoop(bot).run_as_thread()
    print("Listening...")

    while 1:
        time.sleep(10)
