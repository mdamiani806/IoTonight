import subprocess
import webbrowser
import os
import json
import OwnerClient
import sys
from geopy.geocoders import Nominatim
    
def launchFreeboardConsole():
    # jsonConfFilePath=os.path.dirname(os.path.abspath(__file__))+"\\configuration.json"
    # loaded_json=load_configuration_json(_jsonConfFilePath=jsonConfFilePath)
    # print("\nLaunching freeboard with new club_id: {0} and catalogAddress: {1}\n".format(loaded_json["club_id"],loaded_json['catalog_address']))
    # command="c:\\Users\\mati__000\\Desktop\\Polito\\Programming for IoT applications\\IoTonight - Copia\\FreeboardControl.py"
    # subprocess.Popen(["c:\\Python27\\python.exe",command])
    # webbrowser.open_new("http://192.168.1.63:8091/myfreeboard/?club_id="+str(loaded_json["club_id"])+"&catalog_address="+loaded_json["catalog_address"])#open in new tab

    command=os.path.dirname(os.path.abspath(__file__))+"\\FreeboardControl.py"
    subprocess.Popen(["c:\\Python27\\python.exe",command])
    webbrowser.open_new("http://192.168.1.70:8080/myfreeboard/")#open in new tab

def verifyIfAlreadyRegistered(_loaded_json):
    if(_loaded_json["club_id"]!=""):
        print("...e ben tornato!")
        return True
    else:
        return False

def load_configuration_json(_jsonConfFilePath):
    try:
        with open(_jsonConfFilePath) as data_file:    
            loaded_json = json.load(data_file)
            print(loaded_json)
            return(loaded_json)
    except:
        print ("Si e' verificato un problema nella lettura del file di configurazione")
        sys.exit()

if __name__=="__main__":
    print("Benvenuto sulla piattaforma IoTonight!")

    jsonConfFilePath=os.path.dirname(os.path.abspath(__file__))+"\\configuration.json"
    loaded_json=load_configuration_json(_jsonConfFilePath=jsonConfFilePath)

    if(verifyIfAlreadyRegistered(loaded_json)==False):   #configuration file incomplete ->club registration
        
        wannaRegister=raw_input("Desideri procedere alla registrazione? (s/n) ")
        if(wannaRegister=='s'):
            surname=raw_input("Inserisci il tuo Cognome:\t")
            name=raw_input("Inserisci il tuo Nome:\t")
            birthDate=raw_input("Inserisci la tua data di nascita (gg.mm.aaaa): \t")
            gender=raw_input("Inserisci il tuo genere (m/f):\t")
            mobile=raw_input("Inserisci il tuo numero di cellulare:\t")
            clubName=raw_input("Inserisci il nome del tuo Locale:\t")
            validAddress=False
            while(not validAddress):
                city=raw_input("Inserisci la citta' del tuo locale:\t")
                address=raw_input("Inserisci la via del tuo locale:\t")
                country=raw_input("Inserisci il paese:\t")
                clubAddress=address+","+city+","+country
                try:
                    locator = Nominatim(user_agent='myGeocoder')
                    location = locator.geocode(clubAddress)
                    print('Latitude = {}, Longitude = {}'.format(location.latitude, location.longitude))
                except:
                    print("Indirizzo non valido")
                else:
                    validAddress=True
            owner_raw_input=raw_input("Invia 'ok' per confermare i dati e procedere alla registrazione:\t")
            if(owner_raw_input.lower()=="ok"):
                OwnerClient.MyOwnerClient(_name=name,
                _surname=surname,
                _clubName=clubName,
                _birthDate=birthDate,
                _gender=gender,
                _mobile=mobile,
                _lat=location.latitude,
                _long=location.longitude)
                print("Registrazione effettuata")
                owner_raw_input2=raw_input("\nVuoi avviare subito la piattaforma? (s/n)\t")
                if(owner_raw_input2=='s'):
                    launchFreeboardConsole()
                else:
                    print("Arrivederci!")
            else:
                print("Annullamento in corso")
        else:
            print("Arrivederci")
    else:
        launchFreeboardConsole()

