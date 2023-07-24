import time
import datetime
import paho.mqtt.client as mqtt
import ssl
import json
import _thread
import RPi.GPIO as GPIO
import os
import glob

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# SET GPIO PINS 
GPIO_REG_SOL_VALVE = 24

# Set GPIO direction (IN / OUT)
GPIO.setup(GPIO_REG_SOL_VALVE, GPIO.OUT)

# Initialize status
GPIO.output(GPIO_REG_SOL_VALVE, GPIO.HIGH)

# Temperature Sensor Settings
min_temp = 22.0
max_temp = 45.0

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# Read temperature from the sensor
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

# Calibrate temperature from the sensor
def read_temp():
    CALIBRATED = 0.7  # Adding 0.7 degrees C to measured temp
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = round((float(temp_string) / 1000.0 + CALIBRATED), 1)
        return temp_c

# Regular Solenoid Valve - Turn Off
def turn_off_shower():
    GPIO.output(GPIO_REG_SOL_VALVE, GPIO.HIGH)
    print("Shower turned off")

# Regular Solenoid Valve - Turn On
def turn_on_shower():
    GPIO.output(GPIO_REG_SOL_VALVE, GPIO.LOW)
    print("Shower turned on")

def regular_solenoid_valve():
    shower_status = "off"
    user_input = input("Enter 'on' to turn on the shower, or 'off' to turn it off: ")
    if user_input.lower() == "on":
        shower_status = "on"
        turn_on_shower()  # Turn on the shower
    elif user_input.lower() == "off":
        shower_status = "off"
        turn_off_shower()  # Turn off the shower
    else:
        print("Invalid input. Please enter 'on' or 'off'.")
    return shower_status

# Read temperature from the sensor continuously
def read_temperature():
    while True:
        cal_temperature = read_temp()
        print("Measured Temperature (Calibrated) = ", cal_temperature, " C")
        
        # Check if temperature is outside safe range
        if cal_temperature < min_temp or cal_temperature > max_temp:
            print("Temperature outside safe range. Shower turned off.")
            turn_off_shower()
        
        time.sleep(1)

# Raspberry Pi to AWS Connection Settings
def on_connect(client, userdata, flags, rc):
    print("Connected to AWS IoT: " + str(rc))

client = mqtt.Client()
client.on_connect = on_connect
client.tls_set(ca_certs='./rootCA.pem', certfile='./certificate.pem.crt', keyfile='./private.pem.key', tls_version=ssl.PROTOCOL_SSLv23)
client.tls_insecure_set(True)
client.connect("a1tdnoabcs1ef3-ats.iot.us-east-2.amazonaws.com", 8883, 60)

# Publish (Send) data to AWS
def publishData(txt):
    print(txt)
    while True:
        desired_temp = 31.0  # assigned/hard-coded user desired temp as 29 degrees C
        shower_status = regular_solenoid_valve()
        
        # Check if temperature is outside safe range
        if shower_status == "on" and (read_temp() < min_temp or read_temp() > max_temp):
            print("Temperature outside safe range. Shower turned off.")
            turn_off_shower()
            shower_status = "off"
        
        timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        user = "John Doe"
        print("Timestamp = ", timestamp)
        print("User = ", user)
        print("Shower Temperature Setting = ", desired_temp, " C")
        print("Shower Status = ", shower_status)
        print("\n")

        client.publish(
            "raspi/data",
            payload=json.dumps({
                "timestamp": timestamp,
                "cal_temperature": None,  # Set to None as we're not publishing the actual temperature
                "desired_temperature": desired_temp,
                "shower_status": shower_status,
                "user": user
            }),
            qos=0,
            retain=False
        )
        time.sleep(1)

_thread.start_new_thread(publishData, ("Spin-up new Thread...",))
_thread.start_new_thread(read_temperature, ())  # Start reading temperature in a separate thread

client.loop_start()

# Keep the main thread running
while True:
    time.sleep(1)

