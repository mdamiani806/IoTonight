import requests
import json
import sys
from requests.exceptions import HTTPError
import os
import random
import string
import socket

#************************************************************************************************
#   Receives club's info in order to create new channel ThingSpeak and initialize its fields
#   Returns channel id and keys
#************************************************************************************************

usersCatalogEP="http://192.168.1.70:8082/UserReg/registerOwnerUser"

class MyOwnerClient(object):

    def __init__(self,_name,_surname,_clubName,_birthDate,_gender,_mobile,_lat,_long):
        
        self.ownerName=_name
        self.ownerSurname=_surname
        self.clubName=_clubName
        self.birthdate=_birthDate
        self.gender=_gender
        self.mobile=_mobile
        self.latitude=_lat
        self.longitude=_long
        self.getHostNameAndIP()

        #Open configuration file and copy all info in local variables
        self.extractInfoFromJSONconfig(os.path.dirname(os.path.abspath(__file__))+"\\configuration.json")
        
        #Register new owner in catalog
        self.userID=self.registerOwnerInCatalog(_catalogAddress=self.catalogAddress,_usersCatalogAddress=usersCatalogEP)
        
        #Get the TSinitializer service's address, and send all data necessary for TS new channel initialization
        TSinitializerAddress=self.getTSinitializerAddress(_catalogAddress=self.catalogAddress)
        TSinfo=self.sendDataToThingspeakInitializer(_thingspeakInitializerURL=TSinitializerAddress) 

        #Extract (from the answer of the TSinitializer service) keys and channelID
        self.extractTSinfo(TSinfo)

        #Register new club on the catalog and get the assigned ID
        clubID=self.registerClubOnCatalog(_catalogAddress=self.catalogAddress)

        #Store the club id on the configuration file
        self.updateConfigurationFile(_clubID=clubID)

        #Get the FBinitializer service's address, and send all data necessary for the modification of the FB json
        FBinitializerAddress=self.getFBinitializerAddress(_catalogAddress=self.catalogAddress)
        self.objData = self.loadFile(os.path.dirname(os.path.abspath(__file__))+"\\freeboard\\dashboard\\dashboard.json")
        print(self.objData)
        print(os.path.dirname(os.path.abspath(__file__))+"\\freeboard\\dashboard\\dashboard.json")
        FBjson=self.sendDataToFreeboardInitializer(_freeboardInitializerURL=FBinitializerAddress,_FBjson=self.objData,_clubID=clubID)
         
        #update freeboard json file
        self.writeJSON(FBjson)
    
    def writeJSON(self,_data):
        print("Writing on file updated json\n")
        try:
            outfile=open(os.path.dirname(os.path.abspath(__file__))+"\\freeboard\\dashboard\\dashboard.json", 'w')
        except OSError:
            print ("Couldn't open the requested json. The freeboard configuration file might be missing")
            sys.exit()
        else: 
            with outfile:
                json.dump(_data, outfile)

    def getHostNameAndIP(self):
        try: 
            self.host_name = socket.gethostname() 
            self.host_ip = socket.gethostbyname(self.host_name) 
            #print("Hostname :  ",self.host_name) 
            #print("IP : ",self.host_ip) 
        except Exception as e: 
            print("Unable to get Hostname and IP")
            print(str(e))
            sys.exit()
    
    def loadFile(self,JSONfile):
        print ('Reading current FB json into local object ')
        try:
            with open(JSONfile) as data_file:    
                return json.load(data_file)
        except json.decoder.JSONDecodeError:
            print ("Error in decoding json. Canceling procedure")
            #sys.exit()
        
    def generateRandomString(self,desiredLength):
        randomID = ''.join([random.choice(string.ascii_letters 
                + string.digits) for n in range(desiredLength)]) 
        return randomID

    def registerClubOnCatalog(self,_catalogAddress):
        print("\nAbout to register Club in catalog with following data")
        myRegistrationData={
            'ownerID': self.userID,
            'name':self.clubName,
            'thingspeak':{
                "user_API_key": self.userAPIkey,
                'read_API_key':self.readAPIkey,
                'write_API_key':self.writeAPIkey,
                'channel_ID':self.channelID
            }
        }
        print(json.dumps(myRegistrationData))
        try:
            response = requests.post(_catalogAddress+"/registerClub",json=myRegistrationData)
            response.raise_for_status()# If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            print('Other error occurred: {}'.format(err))
        else:
            print('Successful registration of new club')
            responseFromClubRegistrationService = json.loads(response.content.decode('utf8'))
            print(responseFromClubRegistrationService["club_id"])
            print("\n")
            return responseFromClubRegistrationService["club_id"]
        ##return club_ID

    def extractTSinfo(self,TSjsonObj):
        if "error" in TSjsonObj:##
            print(TSjsonObj["error"])
            sys.exit()
        self.channelID=TSjsonObj["channel_id"]
        self.writeAPIkey=TSjsonObj["write_API_key"]
        self.readAPIkey=TSjsonObj["read_API_key"]
        self.userAPIkey=TSjsonObj["user_API_key"]


    def getTSinitializerAddress(self,_catalogAddress):
        print("Executing GET towards catalog to get TSinit address")
        try:
            response=requests.get(self.catalogAddress+"/TSinitializerAddress")
            response.raise_for_status()
            responseObj=json.loads(response.content.decode('utf8'))
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            print('Other error occurred: {}'.format(err)) 
        else:
            print("Here's the response:")
            print(responseObj['TSinitAddress'])
            print("\n")
            return responseObj['TSinitAddress']
    
    def getFBinitializerAddress(self,_catalogAddress):
        print("Executing GET towards catalog to get FBinit address")
        try:
            response=requests.get(self.catalogAddress+"/FBinitializerAddress")
            response.raise_for_status()
            responseObj=json.loads(response.content.decode('utf8'))
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            print('Other error occurred: {}'.format(err))
        else:
            print("Here's the response:")
            print(responseObj['FBinitAddress'])
            return responseObj['FBinitAddress']

    def registerOwnerInCatalog(self,_catalogAddress,_usersCatalogAddress):
        print("\nOwner registration")
        myOwnerRegistrationData={
            'name':self.ownerName,
            'surname':self.ownerSurname,
            'birth':self.birthdate,
            'gender':self.gender,
            'mobile':self.mobile}
        print(json.dumps(myOwnerRegistrationData))
        try:
            print(_usersCatalogAddress)
            response = requests.post(_usersCatalogAddress,json=myOwnerRegistrationData)
            response.raise_for_status() # If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            print('Other error occurred: {}'.format(err)) 
        else:
            responseFromOwnerRegistration = json.loads(response.content.decode('utf8'))
            if "already_registered" in responseFromOwnerRegistration:
                ownerResp=input("Can you confirm you have already registered? (s/n)")
                if(ownerResp=='s'):
                    print('UserID: {}'.format(responseFromOwnerRegistration['already_registered']))
                    print("\n")
                    return responseFromOwnerRegistration['already_registered']
                else:
                    print("We are sorry, an error have occurred")
            print('Successful registration of new owner!')
            print('UserID: {}'.format(responseFromOwnerRegistration['userID']))
            print("\n")
            return responseFromOwnerRegistration['userID']


    def sendDataToThingspeakInitializer(self,_thingspeakInitializerURL):
        dataToSend={
            #"user_API_key":self.userAPIkey,
            "club_name":self.clubName,
            "owner_name":self.ownerName,
            "owner_surname":self.ownerSurname
        }
        try:
            response = requests.post(_thingspeakInitializerURL,json=dataToSend)#create channel and fields
            response.raise_for_status()# If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            print('Other error occurred: {}'.format(err)) 
        else:
            print('Successful GET of TS data from ThingSpeakInitializerURL! And here is the response:')
            responseFromTS = json.loads(response.content.decode('utf8'))
            print(responseFromTS)
            print("\n")
        finally:
            return responseFromTS

    def sendDataToFreeboardInitializer(self,_freeboardInitializerURL,_FBjson,_clubID):
        print("\nSending data and FB json to FBInitializer:")
        dataToSend={
            "channel_id":self.channelID,
            "club_id":_clubID,#new 1/03
            "club_name":self.clubName,
            "user_API_key":self.userAPIkey,
            "read_API_key":self.readAPIkey,
            "FB_json":json.dumps(_FBjson),
            "club_latitude":self.latitude,
            "club_longitude":self.longitude
        }
        try:
            response = requests.post(_freeboardInitializerURL,json=dataToSend)#create channel and fields
            response.raise_for_status()# If the response was successful, no Exception will be raised
        except HTTPError as http_err:
            print('HTTP error occurred: {}'.format(http_err))
        except Exception as err:
            print('Other error occurred: {}'.format(err)) 
        else:
            print('Successful initialization of Freeboard! Here is the updated json:')
            responseFromFB = json.loads(response.content.decode('utf8'))
            print(responseFromFB)
            print("\n")
            return responseFromFB

    def updateConfigurationFile(self,_clubID):
        self.loaded_json["club_id"]=_clubID
        with open(os.path.dirname(os.path.abspath(__file__))+'\\configuration.json', 'w') as outfile:#different configuration files for each channel
            json.dump(self.loaded_json, outfile)

    def extractInfoFromJSONconfig(self,_jsonFilePath):
        try:
            with open(_jsonFilePath) as data_file:    
                self.loaded_json = json.load(data_file)
        except:
            print ("Error in decoding json. Canceling procedure")
            sys.exit()
        else:
            self.catalogAddress=self.loaded_json["catalog_address"]
            #self.userAPIkey=self.loaded_json["user_API_key"]
            print("\nExtracted data from json config:\ncatalog address: {}".format(self.catalogAddress))
