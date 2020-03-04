import json
import cherrypy
import sys,os
import requests
from requests.exceptions import HTTPError
import threading
import time
import socket

#************************************************************************************************
#   (Periodical registration on catalog)
#   Receives club's, owner's and Thingspeak's info as well as the basic json in order to initialize the freeboard page
#   Returns json updated
#************************************************************************************************

catalogAddress="http://192.168.1.70:8085"

class MyFreeboardInitializer(object):
    exposed=True
    
    def __init__(self,_port):
        self.port=_port
        try:
            self.host_ip = socket.gethostbyname(socket.gethostname()) 
            # print("Hostname :  ",self.host_name) 
            print("IP : ",self.host_ip)
            print("port: ",self.port)
        except Exception as e: 
            print("Unable to get Hostname and IP")
            print(str(e))
        else:
            self.address="http://"+self.host_ip+":"+str(self.port)+"/FBinitializer"
            print(self.address)
            RegisterOnCatalogThread("registerOnCatalogThread",catalogAddress,self.address).start()#missing catalog address
    

    def POST(self,*uri,**params):
        print("Freeboard initializer------------------------------------------------------")
        # print("Received POST request with following parameters:")
        # print(params)
        # print("\n")

        if(len(uri)>0 and uri[0]=="FBinitializer"):
            try:
                body=cherrypy.request.body.read()
                json_body=json.loads(body.decode('utf-8'))
                #print(json_body)
                self.channelID=json_body["channel_id"]
                self.clubID=json_body["club_id"]#new 1/03
                self.clubName=json_body["club_name"]
                self.userAPIkey=json_body["user_API_key"]
                self.readAPIkey=json_body["read_API_key"]
                self.club_lat=json_body["club_latitude"]
                self.club_long=json_body["club_longitude"]
                self.objData=json.loads(json_body["FB_json"])#new da debuggare
                print(self.objData)
                #input()
                self.modifyDatasource(_datasource="ThingSpeakLast1",_fieldID=1)#insert correct channel ID and field id in the given datasource
                self.modifyDatasource(_datasource="ThingSpeakLast2",_fieldID=2)#insert correct channel ID in the given datasource
                self.modifyDatasource(_datasource="ThingSpeakLast3",_fieldID=3)#insert correct channel ID in the given datasource
                
                self.modifyChartsSources() #insert correct channel ID and api key in charts
                self.updateClubName() #edit the Club Name
                self.updateMapsCoordinates() #edit maps coordinates
                self.updateFormSubmitEndPoint()
                self.updateMessageSubmitEndPoint()
                #self.updateLivePhotoUrl()
                
                self.modifyFeedSource("Current event","Average age","ThingSpeakLast1",1) 
                self.modifyFeedSource("Current event","% participants","ThingSpeakLast2",2)
                self.modifyFeedSource("Current event","%% genders","ThingSpeakLast3",3) #double %% to have % in string
            except:
                raise cherrypy.HTTPError(500)
            else:
                return json.dumps(self.objData)

    

    def updateFormSubmitEndPoint(self):
        for pane in self.objData["panes"]:
            if(pane["title"]=="set max number of participants"):
                print(pane)
                for widget in pane["widgets"]:
                    if(widget["type"]=="html"):
                        widget["settings"]["html"]='''<form 
                        action=\"'''+catalogAddress+'''/setMaxParticipantsThreshold\" 
                        id=\"myID\" 
                        target=\"ifrm1\"
                        method=\"post\">\n 
                        <br><br>\n  
                        <center> <input type=\"number\" 
                            value=\"20\" 
                            id=\"inputNumber\" 
                            style=\"margin-right:10px;height:30px;width: 80px;\" 
                            name=\"inputParticipants\" 
                            min=\"1\">\n 
                        <input type=\"hidden\" 
                            value=\"'''+self.clubID+'''\" 
                            id=\"clubID\"  
                            name=\"club_id\">\n 
                        <input type=\"submit\" 
                            style=\"width: 80px;font-weight: bold;  color: #FFFFFF; background-color: #5995DA;  border: none;  border-radius: 3px;  padding: 10px 40px; cursor: pointer;padding-left: 0px;padding-right: 0px;\" 
                            value=\"Submit\" 
                            style=\"width: 65px;\">
                        </center>\n</form>
                        <iframe id=\"ifrm1\" name=\"ifrm1\" style=\"display:none\"></iframe>'''

    def updateMessageSubmitEndPoint(self):
        for pane in self.objData["panes"]:
            if(pane["title"]=="SEND MESSAGE TO THE SECURITY STAFF"):
                print(pane)
                for widget in pane["widgets"]:
                    if(widget["type"]=="html"):
                        widget["settings"]["html"]='''<form 
                        action=\"'''+catalogAddress+'''/ownerSendMessageToSecurity\" 
                        id=\"myID2\" 
                        target=\"ifrm1\"
                        method=\"post\">
                        <br><br>
                        <center> <input type=\"text\" 
                            value=\"\" 
                            id=\"inputText\" 
                            style=\"margin-right:10px;height:30px;width: 400px;\" 
                            name=\"message\">
                        <input type=\"hidden\" 
                            value=\"'''+self.clubID+'''\" 
                            id=\"clubID\"  
                            name=\"myClub_id\">
                        <input type=\"submit\" 
                            style=\"width: 80px;font-weight: bold;  color: #FFFFFF; background-color: #5995DA;  border: none;  border-radius: 3px;  padding: 10px 40px; cursor: pointer;padding-left: 0px;padding-right: 0px;\" 
                            value=\"Submit\" 
                            style=\"width: 65px;\">
                        </center>
                        </form>
                        <iframe id=\"ifrm1\" name=\"ifrm1\" style=\"display:none\"></iframe>'''

    def updateMapsCoordinates(self):
        for pane in self.objData["panes"]:
            if(pane["title"]=="Position"):
                print(pane)
                for widget in pane["widgets"]:
                    if(widget["type"]=="google_map"):
                        widget["settings"]["lat"]=str(self.club_lat)
                        widget["settings"]["lon"]=str(self.club_long)

    def modifyDatasource(self,_datasource,_fieldID):
        print("Modifying datasource")
        #print(self.objData)
        for datasource in self.objData["datasources"]:#errore in come self.objData is fatto
            if(datasource["name"]==_datasource):#da modificare json di partenza uguale per tutti
                #https://api.thingspeak.com/channels/991988/fields/1/last.json?api_key=XKJJO1R7T004LL7R
                datasource["settings"]["url"]="https://api.thingspeak.com/channels/"+str(self.channelID)+"/fields/"+str(_fieldID)+"/last.json?api_key="+str(self.readAPIkey)
        #print(self.objData)

    def updateClubName(self):
        print("Updating club name")
        for pane in self.objData["panes"]:
            if(pane["title"]=="General Info"):
                print(pane)
                for widget in pane["widgets"]:
                    print(widget)
                    if(widget["settings"]["title"]=="My club"):
                        widget["settings"]["value"]=str(self.clubName)
        #print(self.objData)

    def modifyChartsSources(self):
        print(self.objData)
        print("Modifying charts sources")
        for pane in self.objData["panes"]:
            print(pane)
            if(pane["title"]=="My events trend"):
                pane["widgets"][0]["settings"]["html"]="<iframe width=\"450\" height=\"250\" style=\"border: 1px solid #cccccc;\" src=\"https://thingspeak.com/channels/"+str(self.channelID)+"/charts/"+"1"+"?api_key="+str(self.readAPIkey)+"&dynamic=true&title=Average+Age\"></iframe>"
                pane["widgets"][1]["settings"]["html"]="<iframe width=\"450\" height=\"250\" style=\"border: 1px solid #cccccc;\" src=\"https://thingspeak.com/channels/"+str(self.channelID)+"/charts/"+"2"+"?api_key="+str(self.readAPIkey)+"&dynamic=true&title=Percentage+of+Participants\"></iframe>"
                pane["widgets"][2]["settings"]["html"]="<iframe width=\"450\" height=\"250\" style=\"border: 1px solid #cccccc;\" src=\"https://thingspeak.com/channels/"+str(self.channelID)+"/charts/"+"3"+"?api_key="+str(self.readAPIkey)+"&dynamic=true&title=Percentage+Genders\"></iframe>"
                return
    def modifyFeedSource(self,_paneTitle,_widgetTitle,_dataSourceName,_fieldID):
        print("Modifying feed sources for gauge {}".format(_widgetTitle))
        for pane in self.objData["panes"]:
            if(pane["title"]==_paneTitle):
                for widget in pane["widgets"]:
                    if(widget["settings"]["title"]==_widgetTitle):
                        widget["settings"]["value"]="datasources[\"{}\"][\"field{}\"]".format(_dataSourceName,str(_fieldID))
    
    def cancelProcedure(self,_IDchannel):
        requests.delete("https://api.thingspeak.com/channels/"+str(self.channelID)+".json?api_key="+self.userAPIkey)
        #os.remove(current_dir+'/thingSpeakConfiguration_'+str(_IDchannel)+'.json')

class RegisterOnCatalogThread(threading.Thread):
    def __init__(self, threadID,_catalogAddress,_selfAddress):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.catalogAddress=_catalogAddress
        self.address=_selfAddress
    def run(self):
        while(True):
            print("Registering FBinitializer in catalog")
            try:
                response = requests.post(self.catalogAddress+"/registerFBinitializer",data={"initializer_address":self.address})
                response.raise_for_status()# If the response was successful, no Exception will be raised
            except HTTPError as http_err:
                print('HTTP error occurred: {}'.format(http_err))
                return False
            except Exception as err:
                print('Other error occurred: {}'.format(err))
                return False
            else:
                print('FBinitializer registered')
                decodedResponse = response.content.decode('utf8')
                print(decodedResponse)
            time.sleep(120)

if __name__ == '__main__':
    myport=8085
    conf = {
        '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        },
    }
    cherrypy.tree.mount (MyFreeboardInitializer(myport), '/', conf)
    cherrypy.config.update({'server.socket_host':'192.168.56.1','server.socket_port': myport})
    cherrypy.engine.start()
    cherrypy.engine.block()