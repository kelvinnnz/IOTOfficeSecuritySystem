# Import SDK packages
import gevent
import gevent.monkey
from gevent.pywsgi import WSGIServer 
gevent.monkey.patch_all()
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from datetime import datetime
from gpiozero import MotionSensor, LED
import threading
from picamera import PiCamera
import sys, os
import MySQLdb
from azure.storage.blob import BlockBlobService
from azure.storage.blob import ContentSettings
from flask import Flask, render_template, request, Response
app = Flask(__name__)

global db
global cursor   
global running
global block_blob_service
#green led
ledgreen = LED(26)
#red led
ledred = LED(21)
ms = MotionSensor(27, sample_rate=5, queue_len=1)
camera = PiCamera()

#change to your iot host endpoint
host = "host.iot.us-west-2.amazonaws.com"
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

my_rpi = AWSIoTMQTTClient("basicPubSub")
my_rpi.configureEndpoint(host, 8883)
my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
my_rpi.configureMQTTOperationTimeout(5)  # 5 sec
    
def SystemOff():
  global running
  running = False
  ledgreen.off()
  ledred.on()
  return "System is turned off!"

        
def SystemOn():
    try:
        global running
        running = True
        my_rpi.connect()
        try:
            global block_blob_service
            #insert your azure blob account name and key
            block_blob_service = BlockBlobService(account_name='account_name', account_key='account_key')
            print("blob connected")
            #Connect to database
            db = MySQLdb.connect(host="aws_rds_endpoint",port=3306,user="username",passwd="password ",db="OSS")
            cursor = db.cursor()
            print("Successfully connected to database!")
            ledgreen.on()
            ledred.off()
        except: 
            print("Error connecting to mySQL database") 
            ledred.blink()

        while(running):
                
            if ms.motion_detected == True:
                for x in range(0, 1):
                    timenow = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    imagename = str(timenow) + '.jpg'
                    imagepath = '/home/pi/OSS/static/images/' + imagename
                    print("Motion detected")
                    camera.capture(imagepath)
                    print("Image Name: " + imagename)
                    local_path=os.path.expanduser("~/OSS/static/images")
                    full_path_to_file =os.path.join(local_path, imagename)
                    print(full_path_to_file)
                    block_blob_service.create_blob_from_path('mycontainer',imagename,imagepath,content_settings=ContentSettings(content_type='image/jpeg'))
                    print("blob uploaded")
                    generator = block_blob_service.list_blobs('mycontainer')
                    for blob in generator:
                        if(blob.name == imagename):
                            bloburl = block_blob_service.make_blob_url('mycontainer', blob.name)
                            sql = "INSERT into Image (ImageName, ImagePath) VALUES ('"+imagename+"','"+bloburl+"')"
                            cursor.execute(sql)
                            db.commit()
                    
                    sql = "INSERT into MotionSensor (State) VALUES ('Active')" 
                    cursor.execute(sql)
                    db.commit()
                    sleep(1)
                my_rpi.publish("sensors/motion", 'Motion Detected', 1)
            else:
                print("no motion")
                sleep(1)

    except MySQLdb.Error as e:
        print("sql")
        print e

    except KeyboardInterrupt:
        print ("Program aborted.")
        camera.close()
        cursor.close() 
        db.close()
        gpiozero.cleanup()
        sys.exit()

    except:
        print ("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
        sys.exit()

@app.route("/GetSystem")
def GetSystem():
    if running == True:
        response = "Enabled"
    else:
        response = "Disabled"

    return response 

@app.route("/System/<status>")
def System(status):
    if status == "Enabled":
        thread = threading.Thread(target=SystemOn)
        thread.start()
        
    else:
        SystemOff()

    return ""    
 
# Alarm function.
@app.route("/offAlarm")
def offAlarm():
    my_rpi.publish("sensors/motion", 'sensoroff', 1)
    print("sensor off")

# Set main() to run in the background.
@app.before_first_request
def activate_job():
    def main():
           SystemOn()

    thread = threading.Thread(target=main)
    thread.start()
        

@app.route("/")
def home():
import mysql.connector 
#insert your aws mysql credentials
    u, pw,h,db = 'username', 'password', 'aws_rds_endpoint', 'OSS' 
    data = []
    con = mysql.connector.connect(user=u,password=pw,host=h,database=db) 
    print("Database successfully connected") 
    cur = con.cursor() 
    query = "SELECT ImagePath FROM Image ORDER BY Id DESC " 
    cur.execute(query)
    for ImagePath, in cur:
        imagepath = format(ImagePath)
        data.append(imagepath)
    return render_template('index.html', data = data)


@app.route("/History") 
def chart(): 
    import mysql.connector 
#insert your aws mysql credentials
    u, pw,h,db = 'username', 'password', 'aws_rds_endpoint', 'OSS' 
    chartdata = []
    con = mysql.connector.connect(user=u,password=pw,host=h,database=db) 
    print("Database successfully connected") 
    cur = con.cursor() 
    query = "SELECT Count(State), DATE(DateTime) FROM MotionSensor WHERE State in ('Active') GROUP BY DATE(DateTime) ORDER BY DateTime DESC " 
    cur.execute(query)
    for (State, DateTime) in cur:
        d = []
        ts = str(DateTime)
        d.append(State)
        d.append(ts) 
        chartdata.append(d)
    return render_template('history.html', chartdata = chartdata) 

@app.route("/Setting")
def setting():
    return render_template('setting.html')
   

if __name__ == '__main__':
    try:
        http_server = WSGIServer(('0.0.0.0', 8001), app)
        http_server.serve_forever()
        app.debug = True
        
    except KeyboardInterrupt:
        print("System exit")  

    except:
        print("Exception")

