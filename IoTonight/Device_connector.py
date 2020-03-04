import time
import json
import paho.mqtt.client as mqtt
from Device_agent import Device_agent_pin
import cherrypy
import requests as req
import threading
import socket


def on_connect(client,userdata,flags,rc):
    print("Connected with result code:"+str(rc))

# Classe del thread per mandare periodicamente una post con i MAC address
class PresenceThread (threading.Thread):
   def __init__(self, threadID, name,server_url):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.server_url=server_url
   
   def run(self):
       while True:
           try:
               ListOfMAC=DeviceAgentObj.CheckPart()
               response=req.post(self.server_url,json=ListOfMAC)
               now=time.time()
               print("Informations about MAC addresses sent")
           except:
               print("It was not possible to send information about the participants")

# Classe del thread per la registrazione al server
class RegistrationThread (threading.Thread):
   def __init__(self, threadID, name, server_url):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.server_url = server_url+'/ClubReg'
   def run(self):
       global DeviceAgentObj
       global MQTT_channels
       while True:
            conf_file=DeviceAgentObj.check_devices()
            try:
                response=req.post(self.server_url,json=conf_file)
                if response:
                    response=json.loads(response.content)
                    MQTT_channels=response["MQTT"]
                    DeviceAgentObj.set_maxcapacity(response["max_capacity"])
                    print("Club correctly updated to the server")
                else:
                    print("Cannot connect to the server")
            except:
                print("Cannot connect to the server")

            time.sleep(180)


# Classe del thread per pubblicare stato sensori
class PubblishThread (threading.Thread):
    def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
    def run(self):
        global MQTT_channels
        global client
        global DeviceAgentObj
        while MQTT_channels=="empty":
            pass
        broker=""
        port=0
        while True:
           if broker != MQTT_channels["broker"] or port!=MQTT_channels["port"]:
               broker=MQTT_channels["broker"]
               port=MQTT_channels["port"]
               client.connect(broker,port,60)
               client.loop_start()
           for topic in MQTT_channels["topics"]:
               item=topic.split('/')
               room=item[2]
               descriptor=item[1]
               exec ("body= DeviceAgentObj.read_" + descriptor + '("'+room+'")',locals(),globals())
               client.publish(topic, body)
           time.sleep(10)



# Classe del thread per controllo soglie e invio degli alert
class ThrsThread (threading.Thread):
    def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
    def run(self):
        global MQTT_channels
        global client
        global DeviceAgentObj
        while MQTT_channels=="empty":
            pass
        broker=""
        port=0
        while True:
           if broker != MQTT_channels["broker"] or port!=MQTT_channels["port"]:
               broker=MQTT_channels["broker"]
               port=MQTT_channels["port"]
               client.connect(broker,port,60)
               client.loop_start()
           thrs=DeviceAgentObj.check_thrs()
           if len(thrs)>0:
               for thr in thrs:
                   client.publish("IoTonight/ThreshAlert", json.dumps(thr),qos=2)
           time.sleep(1)



# Canali REST API
class DeviceConnectorWS(object):
    exposed = True

    def __init__(self,DeviceAgentObj): # Leggo file configurazione sensori disponibili
        self.device_agent=DeviceAgentObj
    def GET(self, *uri, **params):
        if uri[0]=="read": #Request of sensors measures
          try:
            exec ("response=self.device_agent.read_" + uri[1] + '("'+uri[2]+'")',locals(),globals())
            if "error" in response:
                raise cherrypy.HTTPError(500)
            else:
              return response
          except:
              raise cherrypy.HTTPError(500)
        else:
            raise cherrypy.HTTPError(400)

    def POST(self,*uri): #Faccio una post se voglio modificare stato degli attuatori
        if len(uri)>0:
          exec ("response=self.device_agent.set_" + uri[0] + "()",locals(),globals())
          return json.dumps({"Response":response})
        else:
          raise cherrypy.HTTPError(400) #incorrect request

if __name__ == '__main__':
    IP=[l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET,socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
    MQTT_channels="empty"
    REST_channles={}

    with open("conf_file.txt") as json_file:
        conf_file = json.load(json_file)
    bn = IP +":8080"+ "/" + conf_file["club_id"]
    conf_file["rest_addr"]="http://"+bn
    DeviceAgentObj = Device_agent_pin(conf_file,bn)

    #Creo thread di registrazione
    reg_thread=RegistrationThread(1,"Thread_reg","http://192.168.1.70:8085")
    reg_thread.start()
    
    pub_thread=PubblishThread(2,"pub_thread")
    pub_thread.start()
    client = mqtt.Client()
    client.on_connect = on_connect

    pres_thread=PresenceThread(3,"pres_thread","http://192.168.1.70:8081/PDE")
    pres_thread.start()

    thrs_thread=ThrsThread(4,"thrs_thread")
    thrs_thread.start()

    DeviceConnObj=DeviceConnectorWS(DeviceAgentObj)
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }

    cherrypy.tree.mount(DeviceConnObj, '/'+conf_file["club_id"], conf)
    cherrypy.config.update({'server.socket_host': IP })
    cherrypy.engine.start()
    cherrypy.engine.block()
