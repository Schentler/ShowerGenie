import RPi.GPIO as GPIO
import time
import glob
import os
import threading
import datetime
import paho.mqtt.client as mqtt
import ssl
import json

# Raspberry Pi to AWS Connection Settings
def on_connect(client, userdata, flags, rc):
    print("Connected to AWS IoT: " + str(rc))
    # Subscribe to the topic when connected
    client.subscribe("raspi/user")

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print("Message received: " + payload)  # Display the received message

    try:
        data = json.loads(payload)
        command = data.get("command")
        if command == "On":
            # Call the function to turn on the shower
            turn_on_shower()

            # Check and set the desired temperature if available in the payload
            desired_temp_str = data.get("desiredTemperature")
            if desired_temp_str:
                set_desired_temperature(desired_temp_str)

            # Check and set the guest name if available in the payload
            guest_name_payload = data.get("userName")
            if guest_name_payload:
                set_guest_name(guest_name_payload)

        elif command == "Off":
            # Call the function to turn off the shower
            turn_off_shower()

        else:
            # Handle unrecognized commands here (if needed)
            print("Invalid command received.")
    except json.JSONDecodeError:
        print("Invalid JSON payload received.")

# MQTT on_connect and on_message callbacks
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.tls_set(ca_certs='./rootCA.pem', certfile='./certificate.pem.crt', keyfile='./private.pem.key', tls_version=ssl.PROTOCOL_SSLv23)
client.tls_insecure_set(True)
client.connect("a1tdnoabcs1ef3-ats.iot.us-east-2.amazonaws.com", 8883, 60)

# Set GPIO mode and pins
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO_REG_SOL_VALVE = 24
SERVO_HOT = 21
SERVO_COLD = 20
GPIO.setup(GPIO_REG_SOL_VALVE, GPIO.OUT)
GPIO.setup(SERVO_HOT, GPIO.OUT)
GPIO.setup(SERVO_COLD, GPIO.OUT)
GPIO.output(GPIO_REG_SOL_VALVE, GPIO.LOW)

# Initialize servos
servo_pwm_hot = GPIO.PWM(SERVO_HOT, 50)
servo_pwm_cold = GPIO.PWM(SERVO_COLD, 50)
servo_pwm_hot.start(0)
servo_pwm_cold.start(0)

# Variable Declaration
min_temp = 22.0
max_temp = 45.0
desired_temp = 30.0
previous_temperature = 0.0
shower_status = "off"
guest_name = ""
accept_temp_diff = 1.0
#servo_pos=0
if desired_temp == 22:
    servo_pos=52
if desired_temp == 23:
    servo_pos=51
if desired_temp == 24:
    servo_pos=49
if desired_temp == 25:
    servo_pos=48
if desired_temp == 26:
    servo_pos=46
if desired_temp == 27:
    servo_pos=45
if desired_temp == 28:
    servo_pos=43
if desired_temp == 29:
    servo_pos=42
if desired_temp == 30:
    servo_pos=40
if desired_temp == 31:
    servo_pos=39
if desired_temp == 32:
    servo_pos=38
if desired_temp == 33:
    servo_pos=36
if desired_temp == 34:
    servo_pos=35
if desired_temp == 35:
    servo_pos=40
if desired_temp == 36:
    servo_pos=33
if desired_temp == 37:
    servo_pos=32
if desired_temp == 38:
    servo_pos=29
if desired_temp == 39:
    servo_pos=27
if desired_temp == 40:
    servo_pos=26
if desired_temp == 41:
    servo_pos=24
if desired_temp == 42:
    servo_pos=23
if desired_temp == 43:
    servo_pos=21
if desired_temp == 44:
    servo_pos=20
if desired_temp == 45:
    servo_pos=19

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
    CALIBRATED = 0.7
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
    global shower_status
    GPIO.output(GPIO_REG_SOL_VALVE, GPIO.HIGH)
    shower_status = "off"
    print("Shower turned off")
    set_servo_position(servo_pwm_hot, 1)
    set_servo_position(servo_pwm_cold, 1)

# Regular Solenoid Valve - Turn On
def turn_on_shower():
    global shower_status
    global servo_pos
    global desired_temp
    GPIO.output(GPIO_REG_SOL_VALVE, GPIO.LOW)
    shower_status = "on"
    print("Shower turned on")
    set_servo_position(servo_pwm_hot, servo_pos)
    set_servo_position(servo_pwm_cold, 57-servo_pos)

# Function to control the servo motor position
def set_servo_position(servo, pwm_signal):     
     servo_pwm_val = (pwm_signal / 18.0) + 2
     servo.ChangeDutyCycle(servo_pwm_val)
     time.sleep(0.3)
 

# Function to set the desired temperature
def set_desired_temperature(desired_temp_str):
    global desired_temp
    try:
        # Extract numerical value from the string and convert to float
        desired_temp = float(desired_temp_str.split("°")[0])
        print(f"Desired temperature set to {desired_temp}°C")
        # Implement code here to handle desired temperature setting (if needed)
    except ValueError:
        print("Invalid desired temperature format. Please use 'XX°C' format.")

# Function to set the guest name (if needed)
def set_guest_name(name):
    global guest_name
    guest_name = name
    print(f"Guest Name: {guest_name}")
    # Implement code here to handle guest name (if needed)

# Function to continuously read temperature and adjust the flow
def temperature_controller():
    global previous_temperature, guest_name, shower_status
    hot_duty_cycle = servo_pos
    cold_duty_cycle = 57 - servo_pos
    while True:
        cal_temperature = read_temp()
        print(f"Current temp: {cal_temperature}°C")

        # Check if temperature is outside safe range
        if cal_temperature < min_temp or cal_temperature > max_temp:
            print("Temperature outside safe range. Shower turned off.")
            turn_off_shower()
        else:
            if shower_status == "on":  # Check if the shower is on before adjusting the flow
                if cal_temperature - desired_temp > accept_temp_diff:
                    # Reduce hot water flow
                    if hot_duty_cycle > 1:
                        hot_duty_cycle -= 1
                        servo_pos = hot_duty_cycle
                    if cold_duty_cycle < 57:
                        cold_duty_cycle += 1
                elif desired_temp - cal_temperature > accept_temp_diff :
                    # Increase hot water flow
                    if hot_duty_cycle < 57:
                        hot_duty_cycle += 1
                        servo_pos = hot_duty_cycle
                    if cold_duty_cycle > 1:
                        cold_duty_cycle -= 1
                else:
                    print("Temperature stay within the acceptable difference.")

                set_servo_position(servo_pwm_hot, hot_duty_cycle)
                set_servo_position(servo_pwm_cold, cold_duty_cycle)

                # Check if the current temperature is different from the previous one
                if cal_temperature != previous_temperature:
                    # Prepare the data to be sent
                    data = {
                        "timestamp": datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                        "cal_temperature": cal_temperature,
                        "desired_temperature": desired_temp,
                        "shower_status": shower_status,
                        "user": guest_name
                    }

                    # Publish the data to the "raspi/data" topic
                    client.publish("raspi/data", payload=json.dumps(data), qos=0, retain=False)

                    # Update the previous temperature
                    previous_temperature = cal_temperature

        time.sleep(1)

# Main code execution
try:
    # Set both hot and cold water servos to 1 (fully closed)
    set_servo_position(servo_pwm_hot, 1)
    set_servo_position(servo_pwm_cold, 1)

    # Start the MQTT message loop in a separate thread
    mqtt_thread = threading.Thread(target=client.loop_forever)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    # Start the temperature_controller function in a separate thread
    temp_controller_thread = threading.Thread(target=temperature_controller)
    temp_controller_thread.daemon = True
    temp_controller_thread.start()

    # Wait for the user to manually stop the program
    while True:
        pass

except KeyboardInterrupt:
    # Clean up GPIO on keyboard interrupt
    GPIO.cleanup()

