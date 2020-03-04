import cherrypy
import json
import random
import threading
import time
import string


lock=threading.Lock()

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class UserCatalog(object):
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

    def CheckReg(self,chat_id):
        chat_id = int(chat_id)
        user = [item for item in self.catalog["users"] if item["chat_id"]==chat_id]
        if len(user) > 0:
            user = user[0]
            return {"isRegistered":1,"category": user["category"],"user_id":user["user_id"]}
        else:
            return {"isRegistered":0,"category": "","user_id":""}

    def Reg(self,details):
        if len(self.catalog["users"]) > 0:
            user_ids=[item["user_id"] for item in self.catalog["users"]]
            users = sorted(user_ids, reverse=True)
            print(users)
            n_user = int(filter(str.isdigit, str(users[0]))) + 1
        else:
            n_user = 1
        new_user=details
        new_user["user_id"]="ui_" + str(n_user)
        new_user["registration_time"]=time.time()
        self.catalog["users"].append(new_user)
        self.update_json()
        return {"isRegistered":1,"category": new_user["category"],"user_id":new_user["user_id"]}

    def InfoMobile(self,mobile_list): #in questa funzione cerco in base alla liste dei numeri di telefono
        users=[{"user_id":item["user_id"],"gender":item["gender"],"birth":item["birth"]} for item in self.catalog["users"] if item["mobile"] in mobile_list]
        return {"users":users}

    def InfoChatid(self,ui_list):
        chat_ids=[user["chat_id"] for user in self.catalog["users"] if user["user_id"] in ui_list]
        return {"chat_ids":chat_ids}

    def registerOwnerUser(self, jsonObj):
        users_tuple = [(i, item) for i, item in enumerate(self.catalog['users']) if (
                item['category'] == 'owner' and
                item['name'] == jsonObj['name'] and
                item['surname'] == jsonObj['surname'] and
                item['birth'] == jsonObj['birth'])]
        if len(users_tuple) > 0:
            user_already_present = users_tuple[0][1]
            print(user_already_present)
            return {"already_registered": user_already_present['user_id']}  # owner already registered with this ID
        else:
            ownerID = 'ui_' + ''.join([random.choice(string.ascii_letters + string.digits) for n in range(3)]),
            print(jsonObj)
            jsonToAddToCatalog = {
                'user_id': ownerID[0],
                'name': jsonObj['name'],
                'surname': jsonObj['surname'],
                'birth': jsonObj['birth'],
                'gender': jsonObj['gender'],
                'mobile': jsonObj['mobile'],
                'category': 'owner',
                'chat_id': '-',
                'registration_time': time.time()
            }
            self.catalog['users'].append(jsonToAddToCatalog)
            self.update_json()
            return {'userID': ownerID[0]}

    def sendBackChatID(self, _params):
        user_id = _params['user_id']
        requested_chat_id = [x for x in self.catalog['users'] if x["user_id"] == user_id]
        print('Requested chat id: {}'.format(requested_chat_id))
        if len(requested_chat_id) == 0:
            return "error"
        else:
            return {'chat_id': requested_chat_id[0]['chat_id']}


class UserRegWS(object):
    exposed = True
    def __init__(self,catalog):
        self.catalogObj = UserCatalog(catalog)

    def GET(self,*uri,**params):
        if len(uri)>0:
            if uri[0]=="CheckReg":
                resp=self.catalogObj.CheckReg(uri[1])
                return json.dumps(resp)
            elif (uri[0] == "getChatID"):
                resp = self.catalogObj.sendBackChatID(params)
                if resp != "error":
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(404)
        else:
            raise cherrypy.HTTPError(400)

    def POST(self,*uri):
        print("A POST: "+ uri[0])
        if len(uri)>0:
            if uri[0]=="Reg":
                body = json.loads(cherrypy.request.body.read())
                resp=self.catalogObj.Reg(json.loads(body))
                return json.dumps(resp)
            elif uri[0]=="InfoMobile": #prende informazioni in base al numero di telefono
                body = json.loads(json.loads(cherrypy.request.body.read()))
                if "mobile_list" in body.keys():
                    resp=self.catalogObj.InfoMobile(body["mobile_list"])
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif uri[0]=="InfoChatid": # restituisce lista di chat_id in base alla lista di user_id
                body = json.loads(cherrypy.request.body.read())
                if "user_ids" in body.keys():
                    resp=self.catalogObj.InfoChatid(body["user_ids"])
                    return json.dumps(resp)
                else:
                    raise cherrypy.HTTPError(400)
            elif uri[0] == "registerOwnerUser":
                loaded_body = json.loads(cherrypy.request.body.read())
                print(loaded_body)
                resp = self.catalogObj.registerOwnerUser(loaded_body)
                return json.dumps(resp)  # returning club id
            else:
                raise cherrypy.HTTPError(400)
        else:
            raise cherrypy.HTTPError(400)




if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tool.session.on': True
        }
    }

    user_cat="UserCatalog.json"

    cherrypy.tree.mount(UserRegWS(user_cat), '/UserReg', conf)
    cherrypy.config.update({'server.socket_host': '192.168.1.70','server.socket_port': 8082})
    cherrypy.engine.start()
    cherrypy.engine.block()