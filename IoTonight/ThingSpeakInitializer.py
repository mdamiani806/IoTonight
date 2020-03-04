import requests
from requests.exceptions import HTTPError
import json
import os
import cherrypy
import threading
import time
import socket

#************************************************************************************************
#   (Periodical registration on catalog)
#   Receives club's info in order to create new channel ThingSpeak and initialize its fields
#   Returns channel id and keys
#************************************************************************************************


catalogAddress="http://192.168.1.70:8085"
userAPIkey="VN4HGXLGXNQFYHAC"

class MyThingspeakInitializer(object):
    exposed=True
    
    def __init__(self,_port):
        
        self.userAPIkey=userAPIkey
        self.port=_port
    
        try:
            self.host_ip = socket.gethostbyname(socket.gethostname())  
            print("IP : ",self.host_ip)
            print("port: ",self.port)
        except Exception as e: 
            print("Unable to get Hostname and IP")
            print(str(e))
        else:
            self.address="http://"+self.host_ip+":"+str(self.port)+"/TSinitializer"
            print(self.address) 
            RegisterOnCatalogThread(threadID="registerOnCatalogThread",_catalogAddress=catalogAddress,_selfAddress=self.address,_uAPIkey=self.userAPIkey).start()#MISSING CATALOG ADDRESS

    def POST(self,*uri,**params):
        print(uri)
        print(params)
        if(len(uri)>0 and uri[0]=="TSinitializer"):
            print("------------------------------------")
            body=cherrypy.request.body.read()
            json_body=json.loads(body.decode('utf-8'))
            channelCorrectlyInitialized=self.initChannel(
                _locationName=json_body["club_name"],
                _ownerName=json_body["owner_name"],
                _ownerSurname=json_body["owner_surname"])
            if(channelCorrectlyInitialized==True):
                return self.prepareJSONresponse()
            else:
                return json.dumps({"error":"Problem with channel init"})

    def prepareJSONresponse(self):
        myJSONobj={
            "channel_id":self.channelID,
            "write_API_key":self.API_key_write,
            "read_API_key":self.API_key_read,
            "user_API_key":self.userAPIkey
        }
        print(myJSONobj)
        return json.dumps(myJSONobj)

    def initChannel(self,_locationName,_ownerName,_ownerSurname):#Channel creation
        print("ThingSpeak initializer------------------------------------------------------")
        myobj = {
        'api_key': self.userAPIkey,
        'name':_locationName,
        'public_flag':"false",
        'field1':'AverageAge',
        'field2':'NumberParticipants',
        'field3':'PercentageGenders'
        }
        print(myobj)
        
        try:
            response = requests.post("https://api.thingspeak.com/channels.json",data=myobj)#create channel and fields
            response.raise_for_status()# If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
            return False
        except Exception as err:
            print('Other error occurred: {}'.format(err)) 
            return False
        else:
            print('Channel successfully created!')
            decodedResponse = response.content.decode('utf8')#.replace("'", '"')
            print(decodedResponse)
            self.extractTSDataFromJSON(decodedResponse)#extract info from newly created channel
            return True

    def extractTSDataFromJSON(self,myjson):
        self.TSdata = json.loads(myjson)
        self.channelID=self.TSdata["id"]
        
        for api_key in self.TSdata["api_keys"]:
            if api_key["write_flag"]==True:
                self.API_key_write=api_key["api_key"]
            else:
                self.API_key_read=api_key["api_key"]


class RegisterOnCatalogThread(threading.Thread):
    def __init__(self, threadID,_catalogAddress,_selfAddress,_uAPIkey):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.catalogAddress=_catalogAddress
        self.address=_selfAddress
        self.userAPIkey=_uAPIkey
    def run(self):
        while(True):# ? bELOW TO BE TESTED
            print("Registering TSinitializer in catalog")
            try:
                response = requests.post(self.catalogAddress+"/registerTSinitializer",data={"initializer_address":self.address,"user_API_key":self.userAPIkey})
                response.raise_for_status()# If the response was successful, no Exception will be raised
            except HTTPError as http_err:
                print('HTTP error occurred: {}'.format(http_err))
                return False
            except Exception as err:
                print('Other error occurred: {}'.format(err))
                return False
            else:
                print('TSinitializer registered')
                decodedResponse = response.content.decode('utf8')
                print(decodedResponse)
            time.sleep(120)


if __name__ == '__main__':
    myport=8089
    conf = {
        '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        },
    }
    cherrypy.tree.mount (MyThingspeakInitializer(myport), '/', conf)
    cherrypy.config.update({'server.socket_host':'192.168.56.1','server.socket_port': myport})
    cherrypy.engine.start()
    cherrypy.engine.block()
