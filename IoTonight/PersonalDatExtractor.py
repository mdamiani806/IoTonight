import cherrypy
import json
import socket
import threading
import paho.mqtt.client as mqtt
import requests as req
import time
from datetime import datetime
import statistics

lock=threading.Lock()

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class PersDataExtr(object):
    def __init__(self, catalog):
        self.catalogFile=catalog
        with open(self.catalogFile) as json_file:
            self.catalog = json.load(json_file)
        self.update_clubs()

    @threaded
    def update_json(self):
        lock.acquire()
        with open(self.catalogFile,'w') as json_file:
            json.dump(self.catalog,json_file)
        lock.release()

    @threaded
    def update_clubs(self):
        while 1:
            try:
                response=req.get("http://192.168.1.70:8085/ClubList")
                if response:
                    response_json=json.loads(response.content)
                    club_list=response_json["ClubList"]
                    local_club_list=[item["club_id"] for item in self.catalog["clubs"]]
                    for club in club_list:
                        if not(club[0] in local_club_list):
                            new_club={"club_id":club[0],"M":0,"F":0,"D":0,"participants":[],"avAge":0}
                            self.catalog["clubs"].append(new_club)
                else:
                    print("Update clubs: request error")
            except:
                print("Update clubs: connection failed")
            self.update_json()
            time.sleep(180)


    @threaded
    def CheckMAC(self,origin,ListofMAC):
        #Find the numbers from the catalog mac_cel
        mobile_list=[item["mobile"] for item in self.catalog["mac_mobile"] if item["mac"] in ListofMAC]
        body_req={"mobile_list":mobile_list}

        response=req.post("http://192.168.1.70:8082/UserReg/InfoMobile",json=json.dumps(body_req))
        if response:
            response_json = json.loads(response.content)
            if response_json["users"]!=[]:
                participants=[item["user_id"] for item in response_json["users"]]
                M=0
                F=0
                D=0
                ages=[]
                for user in response_json["users"]:
                    if user["gender"]=="m":
                        M=M+1
                    elif user["gender"]=="f":
                        F=F+1
                    else:
                        D=D+1
                    age=datetime.strptime(user["birth"], '%d-%m-%Y')
                    ages.append((datetime.today() - age).days/365)
                avAge=statistics.mean(ages)
                index_club=[i for i,club in enumerate(self.catalog["clubs"]) if club["club_id"]==origin]
                if len(index_club)>0:
                    self.catalog["clubs"][index_club[0]]["M"] = M
                    self.catalog["clubs"][index_club[0]]["D"] = D
                    self.catalog["clubs"][index_club[0]]["F"] = F
                    self.catalog["clubs"][index_club[0]]["participants"] = participants
                    self.catalog["clubs"][index_club[0]]["avAge"]=avAge
                    self.UpdateParticipants(origin,participants)
                    self.update_json()
                else:
                    print("Could not find the club_id")
            else:
                index_club = [i for i, club in enumerate(self.catalog["clubs"]) if club["club_id"] == origin]
                if len(index_club) > 0:
                    self.catalog["clubs"][index_club[0]]["M"] = 0
                    self.catalog["clubs"][index_club[0]]["D"] = 0
                    self.catalog["clubs"][index_club[0]]["F"] = 0
                    self.catalog["clubs"][index_club[0]]["participants"] = []
                    self.catalog["clubs"][index_club[0]]["avAge"] = 0
                    self.UpdateParticipants(origin, [])
                    self.update_json()
        else:
            print("Request failed with status code " + response.status_code)

    @threaded
    def UpdateParticipants(self,origin,participants):
        body_req={"club_id":origin,"participants":participants}
        try:
            response=req.post("http://192.168.1.70:8085/UpdateParticipants",json=json.dumps(body_req))
            if response:
                response_json=json.loads(response.content)
                if response_json["isUpdate"]:
                    print("Participants update done")
                else:
                    print("Participants could not be updated")
            else:
                print("Participants could not be updated, request failed with status code "+response.status_code)
        except:
            print("Connection failed")

    def InfoPart(self,club_id):
        club=[item for item in self.catalog["clubs"] if item["club_id"]==club_id]
        if len(club)>0:
            club=club[0]
            return {"Male":club["M"],"Female":club["F"],"Diverse":club["D"]}
        else:
            return "error"

    def InfoPerc(self,club_id):
        club=[item for item in self.catalog["clubs"] if item["club_id"]==club_id]
        if len(club)>0:
            club=club[0]
            if len(club["participants"])!=0:
                return {"m":club["M"]/len(club["participants"])*100,"f":club["M"]/len(club["participants"])*100,"d":club["M"]/len(club["participants"])*100}

            else:
                return {"m": 0,
                        "f": 0,
                        "d": 0}

        else:
            return "error"

    def InfoAge(self,club_id):
        club=[item for item in self.catalog["clubs"] if item["club_id"]==club_id]
        if len(club)>0:
            club=club[0]
            return {"avAge":club["avAge"]}
        else:
            return "error"


class PersDataExtrWS(object):
    exposed = True
    def __init__(self,catalogObj):
        self.catalogObj=catalogObj
    def GET(self,*uri):
        if len(uri)>0:
            resp=self.catalogObj.InfoPart(uri[0])
            if resp != "error":
                return json.dumps(resp)
            else:
                raise cherrypy.HTTPError(400)
        else:
            raise cherrypy.HTTPError(400)
    def POST(self,*uri,**params):
        body=json.loads(cherrypy.request.body.read())
        body=json.loads(body)
        origin=body["bn"].split('/')[1] #Qui dovrebbe esserci il club_id
        listofMAC=body["e"][0]["vs"]
        self.catalogObj.CheckMAC(origin,listofMAC)
        return json.dumps({"isReceived":1})





# Classe del thread per pubblicare info partecipanti
class PubblishThread (threading.Thread):
    def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
    def run(self):
        global Broker_info
        global pdeObj
        global client

        while Broker_info=={} or pdeObj.catalog["clubs"]==[]:
            pass
        broker=""
        port=0
        while True:
            if broker != Broker_info["IP"] or port!=Broker_info["port"]:
               broker=Broker_info["IP"]
               port=Broker_info["port"]
               client.connect(broker,port,60)
               client.loop_start()
            for club in pdeObj.catalog["clubs"]:
                    topic = club["club_id"] + '/' + "genders"
                    body = pdeObj.InfoPerc(club["club_id"])
                    client.publish(topic, json.dumps(body))
                    topic = club["club_id"] + '/' + "age"
                    body = pdeObj.InfoAge(club["club_id"])
                    client.publish(topic, json.dumps(body))
            time.sleep(20)

# Classe del thread chiedere periodicamente info sul broker
class BrokerInfoThread (threading.Thread):
    def __init__(self, threadID, name, server_url):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.server_url = server_url + '/BrokerInfo'

    def run(self):
        global Broker_info
        while True:
            try:
                response = req.get(self.server_url)
                if response:
                    Broker_info = json.loads(response.content)
                else:
                    print("Cannot connect to the server")
            except:
                print("Cannot connect to the server")
            time.sleep(600)

def on_connect(client,userdata,flags,rc):
    print("Connected with result code:"+str(rc))

if __name__ == '__main__':

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }

    client = mqtt.Client()
    client.on_connect = on_connect

    Broker_info={}

    BrkInfo_thread=BrokerInfoThread(1,"BrokerInfo_thread","http://192.168.1.70:8085")
    BrkInfo_thread.start()

    pde_catalog = "PDECatalog.json"
    pdeObj = PersDataExtr(pde_catalog)

    pub_thread=PubblishThread(2,"ParInfo_thread")
    pub_thread.start()

    cherrypy.tree.mount(PersDataExtrWS(pdeObj), '/PDE', conf)
    cherrypy.config.update({'server.socket_host': '192.168.1.70','server.socket_port': 8081})
    cherrypy.engine.start()
    cherrypy.engine.block()
