import cherrypy
import json
import threading
import paho.mqtt.client as mqtt
import requests as req
import time
import telepot

lock=threading.Lock()

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class ThresholdCatalog(object):

    def __init__(self, catalog):
        self.catalogFile=catalog
        with open(self.catalogFile) as json_file:
            self.catalog = json.load(json_file)

    @threaded
    def update_json(self):
        lock.acquire()
        with open(self.catalogFile,'w') as json_file:
            json.dump(self.catalog,json_file)
        lock.release()

    def collect_info(self,thrs):
        self.catalog["thrs"]=thrs
        self.catalog["registration_time"]=time.time()
        self.update_json()

    def getAgents(self,club_id):
        agents=[thr["security_agents"] for thr in self.catalog["thrs"] if thr["club_id"]==club_id][0]
        return agents

    def setLastnotification(self,club_id):
        for i,thr in enumerate(self.catalog["thrs"]):
            if thr["club_id"]==club_id:
                self.catalog["thrs"][i]["last_notification"]=time.time()

    def getLastnotification(self,club_id):
        for i,thr in enumerate(self.catalog["thrs"]):
            if thr["club_id"]==club_id:
                if "last_notification" in self.catalog["thrs"][i].keys():
                    return self.catalog["thrs"][i]["last_notification"]
                else:
                    return 0





def on_connect(client,userdata,flags,rc):
    print("Connected with result code:"+str(rc))

def on_message(client, userdata, message):
    global i_thread
    i_thread=i_thread+1
    Alert=json.loads(str(message.payload.decode("utf-8")))
    # Creo thread di Alert
    print("Alert received from: "+Alert["club_id"])
    reg_thread = AlertThread(i_thread, "Alert_thread",Alert)
    reg_thread.start()



class RegistrationThread(threading.Thread):
    def __init__(self, threadID, name, main_link,user_link):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.main_link=main_link
        self.user_link=user_link

    def run(self):
        global Broker
        global port
        global token
        global client
        global catalogObj

        while True:

            response = req.get(self.main_link)
            thrs = []
            if response:
                response_json = json.loads(response.content)
                if Broker != response_json["broker"]["IP"] or port != response_json["broker"]["port"]:
                    Broker = response_json["broker"]["IP"]
                    port = response_json["broker"]["port"]
                    client.connect(Broker, port, 60)
                    client.loop_start()
                    client.subscribe(("IoTonight/ThreshAlert",2))

                token = response_json["token"]

                # create list of ths objs
                for club in response_json["clubs"]:
                    # Create dict of security agents to fill
                    response_user = req.post(self.user_link, json={"user_ids": club["security_agents"]})
                    if response_user:
                        response_user_json = json.loads(response_user.content)
                        security_agents = response_user_json["chat_ids"]
                    else:
                        security_agents = []
                        print("Could not contact the User Reg.")
                    thrs.append({"security_agents": security_agents, "club_id": club["club_id"]})
            else:
                print("Could not contact the Server")

            catalogObj.collect_info(thrs)

            time.sleep(180)


class AlertThread(threading.Thread):
    def __init__(self, threadID, name, Alert):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.alert=Alert

    def run(self):
        global i_thread
        global catalogObj
        global token
        club_id=self.alert["club_id"]
        last_notif=catalogObj.getLastnotification(club_id)
        if time.time()-last_notif>8:
            security_agents=catalogObj.getAgents(club_id)

            message="ALERT! Critical value for "+self.alert["descriptor"]+" sensor detected in room: "+self.alert["room"] +"."
            if self.alert["action"]!="":
                message=message+"\n" + self.alert["action"] + " is now activated"

            bot=telepot.Bot(token)
            for agent in security_agents:
                bot.sendMessage(agent,message)
                print("Message for threshold: "+self.alert["descriptor"]+" in room "+self.alert["room"])
            catalogObj.setLastnotification(club_id)

        i_thread=i_thread-1






if __name__ == '__main__':
    thrs_catalog="ThrsCatalog.json"
    catalogObj=ThresholdCatalog(thrs_catalog)
    maincatalog_link = "http://192.168.1.70:8080/SecInfo"
    usercatalog_link = "http://192.168.1.70:8082/UserReg/InfoChatid"

    Broker=""
    port=0
    token=""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    i_thread=1

    # Creo thread di registrazione
    reg_thread = RegistrationThread(i_thread, "Thread_reg", maincatalog_link,usercatalog_link)
    reg_thread.start()

while True:
    pass
