import time
import json
import random
from RPi import GPIO
import Adafruit_DHT  # Libreria da importare per leggere i valori dei sensori
import requests
import base64
import pexpect

class Device_agent_pin(object):

    def __init__(self,conf_file,bn):
        self.conf_file=conf_file
        self.bn=bn
        self.users=0
        self.child = pexpect.spawn("bluetoothctl")
        self.child.send("scan on\n")
        GPIO.setmode(GPIO.BCM)
        
    def read_temperature(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="temperature" and item["room"]==room][0]
        if device["isActive"]:
            try:
                setting=device["setting"]
                model = setting["model"]
                pin = setting["pin"]
                exec("sensor = Adafruit_DHT."+ model,locals(),globals())
                humidity, temperature = Adafruit_DHT.read_retry(sensor , pin)
                if temperature is None:
                    return json.dumps({"bn": self.bn + '/' + device["device_id"] , "error": "unavailable measure"})
                else:
                    return json.dumps({"bn": self.bn + '/' + device["device_id"] , "e":[{"n":"temperature","u":"Cel","t":time.time(),"v":temperature}]})
            except:
                return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    def read_humidity(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="humidity" and item["room"]==room][0]
        if device["isActive"]:
            try:
                setting=device["setting"]
                model = setting["model"]
                pin = setting["pin"]
                exec("sensor = Adafruit_DHT."+ model,locals(),globals())
                humidity, temperature = Adafruit_DHT.read_retry(sensor , pin)
                if humidity is None:
                    return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
                else:
                    return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"humidity","u":"%RH","t":time.time(),"v":humidity}]})
            except:
                return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    def read_gas(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="gas" and item["room"]==room][0]
        if device["isActive"]:
            try:
                setting=device["setting"]
                pin = setting["pin"]
                GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
                status=GPIO.input(pin)
                return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"gas","u":"detect","t":time.time(),"v":status}]})
            except:
                return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    def read_photo(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="photo" and item["room"]==room][0]
        if device["isActive"]:
            try:
                setting=device["setting"]
                url = setting["url"]
                if room=="main":
                    if self.users==0:
                        photo = "Pictures/empty_room.jpg"
                    elif self.users<self.conf_file["max_capacity"]:
                        photo = "Pictures/half_room.jpg"
                    else:
                        photo = "Pictures/full_room.jpg"
                else:
                    photo="Pictures/"+room+".jpg"
                
                response=requests.post(url,{"image":base64.b64encode(open(photo,'rb').read())})
                
                if response:
                    response=response.json()
                    return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"photo","u":"url","t":time.time(),"vs":response["data"]["image"]["url"]}]})
                else:
                    return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
            except:
                return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    def read_microphone(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="microphone" and item["room"]==room][0]
        setting=device["setting"]
        if device["isActive"]:
            dB=random.randrange(35,73,1)
            GPIO.setup(setting["pin"], GPIO.OUT)
            if dB<72: #Questo è servito per accendere un led e mostrare che la variabile casuale aveva raggiunto un certo valore
                GPIO.output(setting["pin"],GPIO.LOW)
            else:
                GPIO.output(setting["pin"],GPIO.HIGH)
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"microphone","u":"dB","t":time.time(),"v":dB}]})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    def read_presence(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="presence" and item["room"]==room][0]
        if device["isActive"]:
            if bool(random.getrandbits(1)):
                self.users=self.users+random.randrange(0,5,1)
            else:
                self.users=self.users-random.randrange(0,5,1)
                if self.users<0:
                    self.users=0
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"presence","u":"participants","t":time.time(),"v":self.users}]})

        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    def read_ventilator(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="actuator" and item["descriptor"]=="ventilator" and item["room"]==room][0]
        return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"ventilator","u":"status","t":time.time(),"v":device["isActive"]}]})
    
    
    def read_CheckPart(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="CheckPart" and item["room"]==room][0]
        if device["isActive"]:
            return json.dumps({"bn": self.bn + "/" + device["device_id"] ,"e":[{"n":"CheckPart","u":"status","t":time.time(),"v":device["isActive"]}]})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})
    
    def CheckPart(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="sensor" and item["descriptor"]=="CheckPart" and item["room"]==room][0]
        if device["isActive"]:
            bdaddrs = []
            now=time.time()
            while time.time()-now<60:
                self.child.expect("Device (([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2}))",timeout=None)
                bdaddr = self.child.match.group(1)
                bdaddr = str(bdaddr.decode('utf-8'))
                if bdaddr not in bdaddrs:
                    bdaddrs.append(bdaddr)
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"e":[{"n":"CheckPart","u":"ListOfMAC","t":time.time(),"vs":bdaddrs}]})
        else:
            return json.dumps({"bn": self.bn + '/' + device["device_id"] ,"error": "unavailable measure"})

    
    def set_ventilator(self,room="main"):
        device=[item for item in self.conf_file["devices"] if item["type"]=="actuator" and item["descriptor"]=="ventilator" and item["room"]==room][0]
        setting=device["setting"]
        try:
            if device["isActive"]:
                try:
                    GPIO.setup(setting["pin"], GPIO.OUT)
                    GPIO.output(setting["pin"],GPIO.LOW)
                except:
                    GPIO.output(setting["pin"],GPIO.LOW)
                self.conf_file["devices"][self.conf_file["devices"].index(device)]["isActive"]=0
                return "OFF"
            else:
                try:
                    GPIO.setup(setting["pin"], GPIO.OUT)
                    GPIO.output(setting["pin"],GPIO.HIGH)
                except:
                    GPIO.output(setting["pin"],GPIO.HIGH)
                self.conf_file["devices"][self.conf_file["devices"].index(device)]["isActive"]=1
                return "ON"
        except:
            return "Couldn't set ventilator correctly"
    
    def check_devices(self):
        for i,s in enumerate(self.conf_file["devices"]):
            if s["type"]=="sensor" and s["descriptor"]!="photo":
                exec("response=self.read_" + s["descriptor"] + "('"+s["room"]+"')",locals(),globals())
                if "error" in response:
                    self.conf_file["devices"][i]["isActive"]=0
                else:
                    self.conf_file["devices"][i]["isActive"]=1
            else:
                pass

        return self.conf_file

    def check_thrs(self):
        thrs=[]
        for thr in self.conf_file["thresholds"]:
            exec("response=json.loads(self.read_" + thr["descriptor"] + "('"+thr["room"]+"'))",locals(),globals())
            if "error" in response:
                pass
            else:
                if response["e"][0]["v"]>thr["max_value"]: #ho superato la soglia
                    if thr["action"]!="":
                        exec("response_att=json.loads(self.read_" + thr["action"] + "('"+thr["room"]+"'))",locals(),globals())
                        if response_att["e"][0]["v"]==0:
                            exec("response_att=self.set_" + thr["action"] + "('"+thr["room"]+"')",locals(),globals())
                    thrs.append({"club_id":self.conf_file["club_id"],"descriptor":thr["descriptor"],"room":thr["room"],"action":thr["action"]})
                 
        return thrs

    def set_maxcapacity(self,max_capacity):
        self.conf_file["max_capacity"]=max_capacity
        for i,thr in enumerate(self.conf_file["thresholds"]):
            if thr["room"]=="main" and thr["descriptor"]=="presence":
                self.conf_file["thresholds"][i]["max_value"]=self.conf_file["max_capacity"]
