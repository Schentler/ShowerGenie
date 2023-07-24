import RPi.GPIO as GPIO
import time
import glob
import os
import _thread

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# SET GPIO PINS
GPIO_REG_SOL_VALVE = 24
SERVO_HOT = 21  # GPIO pin number for the hot water servo motor
SERVO_COLD = 20  # GPIO pin number for the cold water servo motor

# Set GPIO direction (IN / OUT)
GPIO.setup(GPIO_REG_SOL_VALVE, GPIO.OUT)
GPIO.setup(SERVO_HOT, GPIO.OUT)
GPIO.setup(SERVO_COLD, GPIO.OUT)

# Initialize status
GPIO.output(GPIO_REG_SOL_VALVE, GPIO.HIGH)
servo_pwm_hot = GPIO.PWM(SERVO_HOT, 50)  # 50 Hz frequency for SG90 servo (change if needed)
servo_pwm_cold = GPIO.PWM(SERVO_COLD, 50)  # 50 Hz frequency for SG90 servo (change if needed)
servo_pwm_hot.start(0)  # Start with a duty cycle of 0 (0 degrees)
servo_pwm_cold.start(0)  # Start with a duty cycle of 0 (0 degrees)

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
    set_servo_position(servo_pwm_hot, 2)  # Rotate hot water servo to 2 PWM signal (fully closed)
    set_servo_position(servo_pwm_cold, 2)  # Rotate cold water servo to 2 PWM signal (fully closed)

# Regular Solenoid Valve - Turn On
def turn_on_shower():
    GPIO.output(GPIO_REG_SOL_VALVE, GPIO.LOW)
    print("Shower turned on")
    set_servo_position(servo_pwm_hot, 29)  # Rotate hot water servo to 29 PWM signal (midway)
    set_servo_position(servo_pwm_cold, 29)  # Rotate cold water servo to 29 PWM signal (midway)

# Function to control the servo motor position
def set_servo_position(servo, pwm_signal):
    servo_pwm_val = (pwm_signal / 18.0) + 2  # Map the PWM signal to the servo's duty cycle
    servo.ChangeDutyCycle(servo_pwm_val)
    time.sleep(0.3)  # Wait for the servo to reach the desired position

def regular_solenoid_valve():
    user_input = input("Enter 'on' to turn on the shower, or 'off' to turn it off: ")
    if user_input.lower() == "on":
        turn_on_shower()  # Turn on the shower
    elif user_input.lower() == "off":
        turn_off_shower()  # Turn off the shower
    else:
        print("Invalid input. Please enter 'on' or 'off'.")

# Read temperature from the sensor continuously and adjust the flow
def read_temperature(desired_temp):
    hot_duty_cycle = 29
    cold_duty_cycle = 29
    while True:
        cal_temperature = read_temp()
        print(f"Desired temp: {desired_temp}°C | Current temp: {cal_temperature}°C")

        # Check if temperature is outside safe range
        if cal_temperature < min_temp or cal_temperature > max_temp:
            print("Temperature outside safe range. Shower turned off.")
            turn_off_shower()
        else:
            if cal_temperature > desired_temp:
                # Reduce hot water flow
                if hot_duty_cycle > 2:
                    hot_duty_cycle -= 5
                if cold_duty_cycle < 57:
                    cold_duty_cycle += 5
            elif cal_temperature < desired_temp:
                # Increase hot water flow
                if hot_duty_cycle < 57:
                    hot_duty_cycle += 5
                if cold_duty_cycle > 2:
                    cold_duty_cycle -= 5

            set_servo_position(servo_pwm_hot, hot_duty_cycle)
            set_servo_position(servo_pwm_cold, cold_duty_cycle)

        time.sleep(1)

# Main code execution
try:
    # Set both hot and cold water servos to 1 (fully closed)
    set_servo_position(servo_pwm_hot, 1)
    set_servo_position(servo_pwm_cold, 1)

    # Ask for desired temperature
    desired_temp = float(input("Enter the desired temperature (in Celsius): "))

    # Ask to turn on or off
    regular_solenoid_valve()

    # Start temperature reading and adjustment
    _thread.start_new_thread(read_temperature, (desired_temp,))

    while True:
        # Continuously adjust if needed (temperature adjustment is done in the read_temperature function)
        time.sleep(1)

except KeyboardInterrupt:
    # Clean up GPIO on keyboard interrupt
    GPIO.cleanup()
