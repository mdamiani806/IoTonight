import os
import requests
import json
import paho.mqtt.client as mqtt
from requests.exceptions import HTTPError
import socket
import threading
import cherrypy
import time
import sys
#************************************************************************************************
#   Periodical registration on catalog
#   Periodical refresh of clubs available and subscribe to all their topic of interest
#   On message received: extracts id, sends it to the catalog to get ThingSpeak API keys and forwards the message in the right channel
#************************************************************************************************

Broker="test.mosquitto.org" #Indirizzo del broker
Broker2="mqtt.eclipse.org"

catalogAddress="http://192.168.1.70:8085"

class MyThingSpeakAdapter(object):
    exposed=True

    def __init__(self,_port):
        print("ThingSpeak adapter------------------------------------------------------")
        
        self.port=_port
        self.getHostIP()
        self.address="http://"+self.host_ip+":"+str(self.port)+""
        RegistrationThread("adapterRegThread",_catalogAddress=catalogAddress,_selfAddress=self.address).start()
        
        self.client=mqtt.Client(client_id="TSadapter",clean_session=False) 
        self.client.on_connect = self.on_connect #if connection succesful the RefreshClubsListAndSubscribeToAllTopics thread is started 
        self.client.on_message = self.on_message
        self.client.connect(Broker2,1883,60)
        self.client.loop_start()
        
        print("About to start the loop")
        while True: #Rimane in ascolto
            pass
    
    def getHostIP(self):
        try: 
            self.host_ip = socket.gethostbyname(socket.gethostname())
            print("IP : ",self.host_ip) 
        except: 
            print("Unable to get Hostname and IP")
            self.host_ip=""
    
    # Definizione delle Callbacks
    def on_connect(self,client,userdata,flags,rc):
        print("Connected with result code:"+str(rc))
        RefreshClubsListAndSubscribeToAllTopics(threadID="subscribeTopicsThread",mqttClient=self.client,_catalogAddress=catalogAddress,_hostIP=self.host_ip).start()

    def on_message(self,client, userdata, message):
        print("\nReceived message '" + str(message.payload) + "' on topic '" + message.topic + "' with QoS " + str(message.qos))
        try:
            decoded_data=json.loads(message.payload.decode("utf-8"))
        except:
            print("Error in decoding json")
        
        self.extractInfoFromTopic(message.topic)
        writeAPIkey=self.getWriteAPIkey(self.extractedClubID)
        if self.extractedTypeOfValue=='age':
            self.sendToThingspeak(_fieldName="field1",_data=int(decoded_data["avAge"]),_writeAPIkey=writeAPIkey)
        elif self.extractedTypeOfValue=='presence':
            self.sendToThingspeak(_fieldName="field2",_data=decoded_data["e"][0]["v"],_writeAPIkey=writeAPIkey)
        elif self.extractedTypeOfValue=='genders':
            self.sendToThingspeak(_fieldName="field3",_data=decoded_data["m"],_writeAPIkey=writeAPIkey)
        
    def extractInfoFromTopic(self,topic):
        listOfContents=topic.split("/")
        self.extractedClubID=listOfContents[0]
        self.extractedTypeOfValue=listOfContents[1]
        print("\nData extracted from topic:\nClub id-> {0}\ntype of value-> {1}".format(self.extractedClubID,self.extractedTypeOfValue))
        

    def getWriteAPIkey(self,clubID):
        print("\n\tGetting Write API key...")
        try:
            response=requests.get(catalogAddress+"/writeAPIkey?clubID="+str(clubID))
            loadedResponse = json.loads(response.content.decode('utf8'))
            writeAPIkey=loadedResponse['write_API_key']
        except HTTPError as http_err:
            print("HTTP error occurred: {}".format(http_err))
        except Exception as err:
            print("Other error occurred: {}".format(err))
        else:
            print("\tWrite_API_key-> {} \n".format(writeAPIkey))
            return writeAPIkey
        
    #RESTful interface towards thingspeak
    def sendToThingspeak(self,_fieldName,_data,_writeAPIkey):
        myobj = {"api_key": _writeAPIkey,str(_fieldName):str(_data)}
        try:
            response = requests.post("https://api.thingspeak.com/update.json",data=myobj)
            print(response)
            response.raise_for_status()# If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print("HTTP error occurred: {}".format(http_err))
        except Exception as err:
            print("Other error occurred: {}".format(err))
        else:
            print('Data successfully forwarded at the address {1}: {0}'.format(myobj,"https://api.thingspeak.com/update.json"))
    
class MyThread(threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
    def run(self):
        pass

class RefreshClubsListAndSubscribeToAllTopics(MyThread):#to be tested
    def __init__(self,threadID,mqttClient,_catalogAddress,_hostIP):
        MyThread.__init__(self,threadID)
        self.mqttClient=mqttClient
        self.catalogAddress=_catalogAddress
        self.hostIP=_hostIP

    def run(self):
        while(True):
            print("\n--------------------------------------------------")
            print("Refreshig club list")
            print("--------------------------------------------------")
            try:
                response=requests.get(self.catalogAddress+"/clubsIDList?sender="+str(self.hostIP))
                response.raise_for_status()# If the response was successful, no Exception will be raised
            except HTTPError as http_err:
                print("HTTP error occurred: {}".format(http_err))
            except Exception as err:
                print("Other error occurred: {}".format(err))
            else:
                loadedResponse = json.loads(response.content.decode('utf8'))
                print("Subscribing to topics:\n")
                for clubID in loadedResponse['listOfClubsIDs']:
                    print("\t{0}\t{1}\t{2}".format(str(clubID)+'/genders/#',str(clubID)+'/presence/#',str(clubID)+'/age/#'))
                    print("\t---------")
                    self.mqttClient.subscribe(str(clubID)+'/genders')
                    self.mqttClient.subscribe(str(clubID)+'/presence/#')
                    self.mqttClient.subscribe(str(clubID)+'/age')
                time.sleep(30)#executed avery 30 seconds
        

class RegistrationThread(MyThread):
    def __init__(self,threadID,_catalogAddress,_selfAddress):
        MyThread.__init__(self,threadID)
        self.catalogAddress=_catalogAddress
        self.selfAddress=_selfAddress
    
    def run(self):
        while(True):
            self.registerOnCatalog(self.catalogAddress)
            time.sleep(60)#registration every minute

    def registerOnCatalog(self,_catalogAddress):
        print("Registering on catalog...")
        myObj = {'adapter_address': str(self.selfAddress)}
        try:
            response = requests.post(_catalogAddress+"/registerTSadapter",data=myObj) 
            response.raise_for_status()# If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print("HTTP error occurred: {}".format(http_err))
        except Exception as err:
            print("Other error occurred: {}".format(err)) 
        else:
            print('Adapter successfully registered on MainCatalog!')


if __name__ == '__main__':
    myport=8083
    conf = {
        '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        },
    }
    cherrypy.tree.mount (MyThingSpeakAdapter(myport), '/', conf)
    cherrypy.config.update({'server.socket_host':'192.168.1.63','server.socket_port': myport})
    cherrypy.engine.start()
    cherrypy.engine.block()