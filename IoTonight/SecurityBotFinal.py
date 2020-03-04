# SecurityBot
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
        self.key = ""
        self.stato = "start"
        self.RegStat = 0
        self.keysReg = ["name", "surname",
                        "birth", "gender", "mobile"]
        self.dicReg = {}
        self.info = {"category": ""}

    def check_agent(self, msg, chat_id):
        URL = "http://192.168.1.70:8080/CheckSecurity/user_id/"
        response = requests.get(URL + str(self.info["user_id"]))
        if response:
            # {"isCorrect": 0/1, "club_id": club_id}
            response_json = json.loads(response.content)
            if response_json["isCorrect"]:
                self.stato = "entered"
                self.club_id = response_json['club_id']
                self.load_rooms(msg, chat_id)
            else:
                bot.sendMessage(
                    chat_id, "The key is incorrect, please try again.")
        else:
            bot.sendMessage(
                chat_id, "Connection failed. Please try again later.")

    def check_key(self, msg, chat_id):
        self.key = msg['text']
        URL = "http://192.168.1.70:8080/CheckSecurity/security_key/"
        response = requests.get(URL + str(self.key))
        if response:
            response_json = json.loads(response.content)
            if response_json["isCorrect"]:
                bot.sendMessage(chat_id, "Hi " + msg["from"]["first_name"] +
                                ", the inserted key is correct, now please insert some data for the service registration.")
                self.stato = "registration"
                self.user_reg(chat_id)
            else:
                bot.sendMessage(
                    chat_id, "The key is incorrect, please try again.")
                self.stato = "start"
        else:
            bot.sendMessage(
                chat_id, "Connection failed. Please try again later.")
            self.stato="start"

    def user_reg(self, chat_id):
        if self.keysReg[self.RegStat] == "birth":
            bot.sendMessage(chat_id, "Insert your birth date (dd-mm-yyyy): ")
        elif self.keysReg[self.RegStat] == "gender":
            bot.sendMessage(chat_id, "What is your gender (m/f/d)?")
        else:
            bot.sendMessage(chat_id, "What's your " +
                            self.keysReg[self.RegStat] + "?")
    def securitylist(self, msg, chat_id, user_id, security_key):
        URL = "http://192.168.1.70:8080/CheckSecurity/"
        body_request = {"security_key": security_key, "user_id": user_id}
        # Restituisce {"club_id": club_id, "isChecked": 0/1}
        response = requests.put(URL, json=json.dumps(body_request))
        if response:
            response_json = json.loads(response.content)
            if response_json['isChecked']:
                self.stato = "entered"
                self.club_id = response_json['club_id']
                self.load_rooms(msg, chat_id)
        else:
            bot.sendMessage(
                chat_id, "Connection failed. Please try again later.")

    def check_reg(self, chat_id):
        URL = "http://192.168.1.70:8082/UserReg/CheckReg/"
        response = requests.get(URL + str(chat_id))
        if response:
            return json.loads(response.content)
        else:
            self.stato = "start"
            bot.sendMessage(
                chat_id, "Connection failed. Please try again later.")
            return {"category": "FailedConnection"}

    def load_rooms(self, msg, chat_id):
        URL = "http://192.168.1.70:8080/EndPoints/read_rest/" + self.club_id
        # Riceve -> {'read_rest':[{'room':nome_stanza,'descriptor':tipo_sensore[photo],'URL':url_sensore},{...,...,...}}
        response = requests.get(URL)
        sensorlinks = json.loads(response.content)
        sensorlinks = sensorlinks['read_rest']
        rooms=[]
        for room in sensorlinks: #Faccio una lista di stanze del locale
            if room['room'] not in rooms:
                rooms.append(room['room'])
        buttons = []
        for room in rooms:
            buttons.append(InlineKeyboardButton(
                text=room, callback_data="room"+'/'+self.club_id+'/'+room)) #Al callback data gli passo tutti gli indirizzi della stanza scelta
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[buttons]
            )
        bot.sendMessage(
            chat_id, "Hi " + msg["from"]["first_name"] + ", choose a room to check: ", reply_markup=keyboard
        )

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if self.stato == "start":
            if self.info['category'] == "":
                self.info = self.check_reg(chat_id)
                if self.info["category"] != "security":
                    bot.sendMessage(
                        chat_id, "Hi " + msg["from"]["first_name"] + ", please insert the key to register: ")
                    self.stato = "wait"
                else:
                    self.check_agent(msg, chat_id)
        elif self.stato == "wait":
            self.check_key(msg, chat_id)
        elif self.stato == "registration":
            self.dicReg[self.keysReg[self.RegStat]] = msg["text"]
            self.RegStat += 1
            if self.RegStat < len(self.keysReg):
                self.user_reg(chat_id)
            else:
                self.stato = "start"
                self.dicReg["chat_id"] = chat_id
                self.dicReg["category"] = "security"
                URL = "http://192.168.1.70:8082/UserReg/Reg/"
                response = requests.post(URL, json=json.dumps(self.dicReg))
                if response:
                    response_json = json.loads(response.content)
                    if response_json["isRegistered"]:
                        bot.sendMessage(
                            chat_id, "Thank you " + msg["from"]["first_name"] + ", you are now registered to IoTonight_Security system!")
                        self.securitylist(msg, chat_id,
                                          response_json["user_id"], self.key)
                    else:
                        bot.sendMessage(
                            chat_id, "Connection failed, please try again later.")
                else:
                    bot.sendMessage(
                        chat_id, "Connection failed, please try again later.")

        elif self.stato == "entered":
            self.stato = "entered"
            self.load_rooms(msg, chat_id)

    def on_callback_query(self, msg):
        query_id, chat_id, query_data = telepot.glance(
            msg, flavor="callback_query")
        if query_data[0:4]=="room":
            query_data=query_data.split('/')
            URL = "http://192.168.1.70:8080/EndPoints/read_rest/" + query_data[1] # Riceve -> {"read_rest":[{"room":nome_stanza,"descriptor":tipo_sensore[photo],"URL":url_sensore},{...,...,...}}
            response = requests.get(URL)
            sensorlinks = json.loads(response.content)
            sensorlinks = sensorlinks["read_rest"]
            message = "These are the room informations: " + '\n'
            actuators=[]
            for sensor in sensorlinks:
                if sensor["room"]==query_data[2] and sensor["descriptor"]!="photo":
                    # Qui controlla che la tupla sensor che contiene (stanza,tipodisensore,URL) sia un sensore della stanza "room1" che e' quella che mostriamo agli utenti, e che sia del tipo di uno della lista SensorList
                    URL = sensor["URL"]
                    try:
                        response = requests.get(URL)
                        response_json = json.loads(response.content)
                        sensorvalue = str(response_json["e"][0]["v"])
                        sensorunit = response_json["e"][0]["u"]
                        if len(sensorvalue)>3:
                            sensorvalue=sensorvalue[0:4]
                        if sensorunit=="status":
                            actuators.append(sensor["descriptor"])
                            if sensorvalue=="1":
                                message = message + sensor["descriptor"] + ": " + "ON"+ '('+sensor["type"]+')'+"\n"
                            else:
                                message = message + sensor["descriptor"] + ": " + "OFF" + '('+sensor["type"]+')'+ "\n"
                        else:
                            message = message + sensor["descriptor"] + ": " + \
                                      sensorvalue + " " + sensorunit + "\n"
                    except:
                        message = message + \
                                  sensor["descriptor"] + ": " + "Unavailable" "\n"
                elif sensor["room"]==query_data[2] and sensor["descriptor"] == "photo":
                        URLphoto = sensor["URL"]


            try:
                response = requests.get(URLphoto)
                response_json = json.loads(response.content)
                URLphoto = response_json["e"][0]["vs"]
                bot.sendPhoto(chat_id, URLphoto, caption=message)
            except:
                bot.sendMessage(chat_id, message)

            if len(actuators)>0:
                URL = "http://192.168.1.70:8080/EndPoints/set_rest/" + query_data[1]
                # Riceve -> {"read_rest":[{"room":nome_stanza,"descriptor":tipo_sensore[photo],"URL":url_sensore},{...,...,...}}
                response = requests.get(URL)
                actuatorlinks = json.loads(response.content)
                actuatorlinks = actuatorlinks["set_rest"]
                buttons=[]
                for actuator in actuatorlinks:
                    if actuator["room"]==query_data[2]:
                        buttons.append(InlineKeyboardButton(
                            text=actuator["descriptor"],
                            callback_data=actuator["URL"]))
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[buttons]
                        )
                if len(buttons)>0:
                    bot.sendMessage(
                        chat_id, "You can choose to change status to one of the following actuators: ", reply_markup=keyboard
                    )
            bot.sendMessage(chat_id, "Click here to reload the rooms ---> /start")
        else:
            response = requests.post(query_data)
            actuator_status = json.loads(response.content)
            bot.sendMessage(chat_id, "Status of the selected actuator is now: "+actuator_status["Response"])



if __name__ == "__main__":

    TOKEN = "1003608093:AAEgixlk1gP2F4ldLWQl6J512T_R0h-Wn7k"
    bot = telepot.DelegatorBot(TOKEN, [
        include_callback_query_chat_id(
            pave_event_space())(
            per_chat_id(), create_open, TelegramBot, timeout=200),
    ])
    """bot = telepot.DelegatorBot(TOKEN, [
        pave_event_space()(
            per_chat_id(), create_open, TelegramBot, timeout=200),
        pave_event_space()(
            per_callback_query_origin(), create_open, TelegramBot, timeout=200)
    ])"""
    MessageLoop(bot).run_as_thread()
    print("Listening...")

    while 1:
        time.sleep(10)
