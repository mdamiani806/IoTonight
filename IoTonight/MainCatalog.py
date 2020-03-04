import cherrypy
import json
import socket
import time
import threading
import sys
import string
import random
import telepot
import requests

lock=threading.Lock()
usersCatalogAddress="http://192.168.1.70:8082"

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class CloudIoTonight(object):
    def __init__(self, catalog):
        self.catalogFile=catalog
        with open(self.catalogFile) as json_file:
            self.catalog = json.load(json_file)
        self.topics={}
        self.clubsControl

    @threaded
    def update_json(self):
        lock.acquire()
        with open(self.catalogFile,"w") as json_file:
            json.dump(self.catalog,json_file)
        lock.release()

    def registerClub(self,jsonObj):
        #jsonObj=json.loads(_body)
        #print(jsonObj)
        #print(jsonObj['name'])
        club_tuple = [(i,item) for i,item in enumerate(self.catalog['clubs']) if (item['name'] == jsonObj['name'])]#and item["last_registration_time"]!=None)]
        if len(club_tuple) > 0:
            return "error"#club already registered
        else:
            club_ID='cl_'+''.join([random.choice(string.ascii_letters + string.digits) for n in range(3)])
            jsonToAddToCatalog={
                'name':jsonObj['name'],
                'owners':[jsonObj['ownerID']],
                'security_agents':[],
                'club_id':club_ID,
                'security_key':''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)]),
                'participants':[],
                'max_capacity':0,
                'last_registration_time':None,
                'thingspeak':{
                    'write_API_key':jsonObj['thingspeak']['write_API_key'],
                    'read_API_key':jsonObj['thingspeak']['read_API_key'],
                    'channel_ID':jsonObj['thingspeak']['channel_ID']
                },
                'devices':[]
            }
            self.catalog['clubs'].append(jsonToAddToCatalog)
            self.update_json()
            return {"club_id":club_ID}

    def registerTSinitializer(self, _params):
        try:
            self.catalog['thingspeak']['user_API_key'] = _params['user_API_key']
            self.catalog['thingspeak']['initializer_address'] = _params['initializer_address']
            self.catalog['thingspeak']['initializer_last_update'] = time.time()
            self.update_json()
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return "error"
        return "ok"

    def registerFBinitializer(self, _params):
        try:
            self.catalog['freeboard']['initializer_address'] = _params['initializer_address']
            self.catalog['freeboard']['initializer_last_update'] = time.time()
            self.update_json()
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return "error"
        return "ok"

    def registerTSadapter(self, _params):
        try:
            self.catalog['thingspeak']['adapter_address'] = _params['adapter_address']
            self.catalog['thingspeak']['adapter_last_update'] = time.time()
            self.update_json()
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return "error"
        return "ok"

    def setParticipantsThreshold(self, _params):  # to be tested
        newThreshold = int(_params['inputParticipants'])
        club_id = _params['club_id']
        print(newThreshold)
        print(club_id)
        try:
            for club in self.catalog['clubs']:
                if (club['club_id'] == club_id):
                    club['max_capacity'] = newThreshold
        except:
            return "error"
        else:
            self.update_json()
            return "ok"

    def sendBackTSinitializerAddress(self, _params):
        address = self.catalog['thingspeak']['initializer_address']
        if (address != ""):
            return {"TSinitAddress": address}
        else:
            return "error"

    def sendBackFBinitializerAddress(self, _params):
        address = self.catalog['freeboard']['initializer_address']
        if (address != ""):
            return {"FBinitAddress": address}
        else:
            return "error"

    def sendBackWriteAPIkey(self, _params):
        club_tuple = [(i, item) for i, item in enumerate(self.catalog['clubs']) if
                      (item['club_id'] == _params['clubID'])]
        #print(club_tuple)
        if len(club_tuple) > 0:
            club = club_tuple[0][1]
            #print(club)
            return {'write_API_key': club['thingspeak']['write_API_key']}
        else:
            return "error"

    def sendBackClubsID(self,_params):
        allIDs=[]
        for club in self.catalog['clubs']:
            allIDs.append(club['club_id'])
        if allIDs==[]:
            return "error"
        return {'listOfClubsIDs':allIDs}

    def ownerSendMessageToSecurity(self, _params):

        current_club_id = _params['myClub_id']
        current_message = _params['message']
        print(_params)
        resp = self.SecInfo()
        print(resp)
        telegram_token = resp["token"]
        print("What I got so far: {0}, {1}, {2}".format(current_club_id, current_message, telegram_token))
        chat_IDs = []
        for club in resp["clubs"]:
            if club["club_id"] == current_club_id:
                for securityAgent in club['security_agents']:
                    print("Security agents found: {}".format(securityAgent))
                    usrsCatalogResponse = requests.get(usersCatalogAddress + "/UserReg/getChatID?user_id=" + securityAgent)
                    loadedResponse = json.loads(usrsCatalogResponse.content.decode('utf8'))
                    chat_IDs.append(loadedResponse['chat_id'])
                break
        self.sendMessageToAllSecurity(_message=current_message, _listSecurityChatIDs=chat_IDs,
                                      _tokenTelegram=telegram_token)
        return "ok"

    def sendMessageToAllSecurity(self, _message, _listSecurityChatIDs, _tokenTelegram):
        bot = telepot.Bot(_tokenTelegram)
        print("----------")
        print(_listSecurityChatIDs)
        for chat_id in _listSecurityChatIDs:
            if chat_id == '-':
                continue
            else:
                print("sending this stuff:\nChat id-> {0}\nMessage-> {1}".format(chat_id, _message))
                bot.sendMessage(chat_id, _message)

    @threaded
    def clubsControl(self):
        while True:
            for club in self.catalog["clubs"]:
                if time.time()-club["last_registration_time"]>300 and club["devices"]!=[]:
                    club["devices"]=[]
                    print("No more response from club: "+club['club_id']+". All the end points have been cleared.")
                    self.update_json()


    def ClubReg(self,body): #Club Registration
        club_tuple = [(i,item) for i,item in enumerate(self.catalog["clubs"]) if item["club_id"] == body["club_id"]]
        if len(club_tuple) > 0:
            club_tuple = club_tuple[0]
            index_club=club_tuple[0]
            club=club_tuple[1]
            club["devices"]=body["devices"]
            topics=[]
            for i,device in enumerate(club["devices"]): #Topics and REST addresses creation
                if device["isActive"]==1 or device["type"]=="actuator":
                    club["devices"][i]["end_points"]={}
                    if device["descriptor"]!="photo" and device["type"]!="actuator":
                        club["devices"][i]["end_points"]["topic"]= club["club_id"] + "/" + device["descriptor"] + "/" + device["room"]+"/"+device["device_id"] #TOPIC
                        topics.append(club["devices"][i]["end_points"]["topic"])
                    club["devices"][i]["end_points"]["read_rest"]=body["rest_addr"] + "/" + "read"+"/"+ device["descriptor"] + "/"+ device["room"]+"/" + device["device_id"] #READ SENSOR/STATUS ATTUATOR
                    if device["type"]=="actuator":
                        club["devices"][i]["end_points"]["set_rest"]=body["rest_addr"] +"/"+ device["descriptor"] + "/" + device["room"]+"/"+ device["device_id"] #SET ATTUATOR


            self.catalog["clubs"][index_club]["devices"]=club["devices"]
            self.catalog["clubs"][index_club]["last_registration_time"]=time.time()

            self. update_json()

            MQTT = {"broker": self.catalog["broker"]["IP"],"port":self.catalog["broker"]["port"], "topics": topics, "timestamp": time.time()}

            return{"MQTT":MQTT,"max_capacity":self.catalog["clubs"][index_club]["max_capacity"]}
        else:
            return "error"
    def ClubList(self):
        list_of_clubs=[(item["club_id"],item["name"]) for item in self.catalog["clubs"]]
        return {"ClubList":list_of_clubs}

    def EndPoints(self,type,club_id):
        if type=="read_rest":
            club=[item for item in self.catalog["clubs"] if item["club_id"]==club_id][0]
            rest_edps=[{"room":item["room"],"descriptor":item["descriptor"],"type":item["type"],"URL":item["end_points"]["read_rest"]} for item in club["devices"] if (item["type"]=="sensor" and item["isActive"]==1) or (item["type"]=="actuator") ]
            return {type:rest_edps}
        elif type=="set_rest":
            club = [item for item in self.catalog["clubs"] if item["club_id"] == club_id][0]
            rest_edps = [{"room": item["room"], "descriptor": item["descriptor"],"type":item["type"], "URL": item["end_points"]["set_rest"]} for item in club["devices"] if item["type"]=="actuator"]
            return {type: rest_edps}
        elif type=="mqtt":
            club = [item for item in self.catalog["clubs"] if item["club_id"] == club_id][0]
            rest_edps = [
                {"room": item["room"], "descriptor": item["descriptor"],"type":item["type"], "topic": item["end_points"]["topic"]} for item in club["devices"] if item["type"]=="sensor" and item["isActive"]==1]
            return {type: rest_edps}
        else:
            return "error"

    def CheckSecurity(self,type,key):
        if type=="security_key":
            club = [item for item in self.catalog["clubs"] if item["security_key"]==key]
        elif type=="user_id":
            club = [item for item in self.catalog["clubs"] if key in item["security_agents"]]
        if len(club)>0:
            club=club[0]
            return {"isCorrect":1,"club_id":club["club_id"]}
        else:
            return {"isCorrect":0,"club_id":""}

    def SecInfo(self):
        clubs=[]
        for club in self.catalog["clubs"]:
            clubs.append({"security_agents":club["security_agents"],"club_id":club["club_id"]})

        return {"clubs":clubs,"broker":self.catalog["broker"],"token":self.catalog["telegram"]["security_bot_token"]}

    def UpdateParticipants(self,body):
        club_id=body["club_id"]
        participants=body["participants"]
        index_club=[i for i,club in enumerate(self.catalog["clubs"]) if club["club_id"]==club_id]
        if len(index_club)>0:
            index_club=index_club[0]
            self.catalog["clubs"][index_club]["participants"]=participants
            self.update_json()
            return {"isUpdate":1}
        else:
            return {"isUpdate":0}

    def UpdateAgents(self,body):
        key = body["security_key"]
        user_id = body["user_id"]
        index_club = [i for i, club in enumerate(self.catalog["clubs"]) if club["security_key"] == key]
        if len(index_club) > 0:
            index_club = index_club[0]
            self.catalog["clubs"][index_club]["security_agents"].append(user_id)
            self.update_json()
            return {"club_id": self.catalog["clubs"][index_club]["club_id"], "isChecked": 1}
        else:
            return {"isChecked": 0}

    def BrokerInfo(self):
        return self.catalog["broker"]

class CloudIoTonightWS(object):
    exposed = True
    def __init__(self,catalog):
        self.catalogObj = CloudIoTonight(catalog)

    def GET(self, *uri, **params):
        if len(uri)>0:
            if uri[0]=="ClubList":
                resp=self.catalogObj.ClubList()
                return json.dumps(resp)
            elif uri[0]=="EndPoints" and len(uri)>2:
                resp=self.catalogObj.EndPoints(uri[1],uri[2])
                if resp!="error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif uri[0]=="CheckSecurity" and len(uri)>1:
                resp=self.catalogObj.CheckSecurity(uri[1],uri[2])
                return json.dumps(resp)
            elif uri[0]== "SecInfo":
                resp = self.catalogObj.SecInfo()
                return json.dumps(resp)
            elif uri[0]== "BrokerInfo":
                resp = self.catalogObj.BrokerInfo()
                return json.dumps(resp)
            elif (uri[0] == "TSinitializerAddress"):
                resp = self.catalogObj.sendBackTSinitializerAddress(params)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif (uri[0] == "FBinitializerAddress"):
                resp = self.catalogObj.sendBackFBinitializerAddress(params)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif (uri[0] == "writeAPIkey"):
                #print("Received request")
                resp = self.catalogObj.sendBackWriteAPIkey(params)
                #print(resp)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)  # o 404 not found?
            elif (uri[0] == "clubsIDList"):
                resp = self.catalogObj.sendBackClubsID(params)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)  # o 404 not found?
            else:
                raise cherrypy.HTTPError(400)
        else:
            raise cherrypy.HTTPError(400)

    def POST(self,*uri,**params):
        if len(uri)>0:
            if uri[0]=="ClubReg": #ClubRegistration
                body = json.loads(cherrypy.request.body.read())
                resp=self.catalogObj.ClubReg(body)
                if resp!="error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif uri[0]=="UpdateParticipants":
                body = json.loads(json.loads(cherrypy.request.body.read()))
                resp = self.catalogObj.UpdateParticipants(body)
                return json.dumps(resp)
            elif (uri[0] == "registerClub"):
                loaded_body = json.loads(cherrypy.request.body.read())
                resp = self.catalogObj.registerClub(loaded_body)
                if resp != "error":
                    return json.dumps(resp)  # returning club id
                else:
                    raise cherrypy.HTTPError(409)
            elif (uri[0] == "registerTSinitializer"):
                resp = self.catalogObj.registerTSinitializer(params)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif (uri[0] == "registerFBinitializer"):
                resp = self.catalogObj.registerFBinitializer(params)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif (uri[0] == "registerTSadapter"):
                resp = self.catalogObj.registerTSadapter(params)
                if resp != "error":
                    return json.dumps({'response': resp})
                else:
                    raise cherrypy.HTTPError(400)
            elif (uri[0] == "setMaxParticipantsThreshold"):
                resp = self.catalogObj.setParticipantsThreshold(params)
                if resp != "error":
                    print("About to answer with {}".format(resp))
                    return json.dumps({'response': resp})
                else:
                    raise cherrypy.HTTPError(400)
            elif (uri[0] == "ownerSendMessageToSecurity"):
                resp = self.catalogObj.ownerSendMessageToSecurity(params)
                if resp != "error":
                    print("About to answer with {}".format(resp))
                    return json.dumps({'response': resp})
                else:
                    raise cherrypy.HTTPError(400)
            else:
                raise cherrypy.HTTPError(400)

        else:
            raise cherrypy.HTTPError(400)

    def PUT(self,*uri):
        if len(uri)>0:
            if uri[0]=="CheckSecurity":
                body = json.loads(json.loads(cherrypy.request.body.read()))
                resp= self.catalogObj.UpdateAgents(body)
                return json.dumps(resp)
            else:
                raise cherrypy.HTTPError(400)
        else:
            raise cherrypy.HTTPError(400)




if __name__ == "__main__":

    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tool.session.on": True
        }
    }
    main_catalog="MainCatalog.json"
    cherrypy.tree.mount(CloudIoTonightWS(main_catalog), "/", conf)
    cherrypy.config.update({"server.socket_host": "192.168.1.70","server.socket_port": 8085})
    cherrypy.engine.start()
    cherrypy.engine.block()
