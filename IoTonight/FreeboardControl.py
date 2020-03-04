import json
import cherrypy
import sys,os
import mimetypes
import myUtils

class FreeboardController(object):
    exposed=True
    def GET(self,*uri):
        if(uri[0]=="myfreeboard"):
            return open(os.path.join(myUtils.main_dir,'index.html'),'r').read()
        #else:
        #    to do error handling
    
    def POST(self,*uri,**params):
        print("------------------------------------")
        print(params["json_string"])
        loaded_json = json.loads(params["json_string"]) #it's a dictionary created from json
        self.writeJSON(loaded_json)

    def writeJSON(self,_data):
        with open(myUtils.json_path, 'w') as outfile:
            json.dump(_data, outfile)

if __name__ == '__main__':
    conf = {
        '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        'tools.staticdir.root': myUtils.main_dir,
        },
        '/js': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': './js'
        },
        
        '/css': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': './css'
        },
        
        '/img': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': './img'
        },
        
        '/dashboard': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': './dashboard'
        },
        
        '/plugins': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': './plugins'
        },

        '/static': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': '.'
        },
    }
    cherrypy.tree.mount (FreeboardController(), '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
