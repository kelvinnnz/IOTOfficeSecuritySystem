# Import SDK packages
from gpiozero import LED, Button, Buzzer
from rpi_lcd import LCD
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from datetime import datetime
from twilio.rest import Client

import time
import telepot
import sys

# Token for telegram bot
my_bot_token = 'bot_key'

# Twilio Token and Information
account_sid = "twillio_id"
auth_token = "twillio_authtoken"
client = Client(account_sid, auth_token)
#enter the phone number you have enter in twillio
my_hp = "+6512345668"
twilio_hp = "+1240468-4002"

# Define the variables to be used
led = LED (21)
bz = Buzzer (26)
lcd = LCD()

# To turn on sensors
def sensorOn():
    led.blink()
    bz.on()
    lcd.text("Alarm is on.", 1)
    sms = "Alarm triggered."
    lcd.text ("SMS Sent.", 2)

    message = client.api.account.messages.create(to= my_hp, from_= twilio_hp, body= sms)

    time.sleep(2)
    lcd.clear()
    
# To turn off sensors
def sensorOff():
    led.off()
    bz.off()
    lcd.text("Alarm is off.", 1)
    return "Alarm is turned off"
    lcd.clear()

# Telegram Bot
def respondToMsg(msg):
    chat_id = msg ['chat']['id']
    command = msg['text']

    print ('Got command: {}' .format(command))

    if command == 'Sensoroff':
        bot.sendMessage(chat_id, sensorOff())

bot = telepot.Bot(my_bot_token)
bot.message_loop(respondToMsg)
print('Listening for RPi commands...')

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")

    if (message.payload == 'Motion Detected'):
        sensorOn()
        
    elif (message.payload == 'sensoroff'):
        sensorOff()
#change to your aws iot endpoint    
host = "awsiotendpoint.iot.us-west-2.amazonaws.com"
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

try:
    my_rpi = AWSIoTMQTTClient("iotJunniusSub")
    my_rpi.configureEndpoint(host, 8883)
    my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

    my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
    my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
    my_rpi.configureMQTTOperationTimeout(5)  # 5 sec

    # Connect and subscribe to AWS IoT
    my_rpi.connect()
except:
    print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])

while True:
    my_rpi.subscribe("sensors/motion", 1, customCallback)
    #change to correct topic
    sleep(2)
