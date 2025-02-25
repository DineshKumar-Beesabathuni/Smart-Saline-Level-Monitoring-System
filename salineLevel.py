import RPi.GPIO as GPIO
import time
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Set GPIO mode to use BCM pin numbering
GPIO.setmode(GPIO.BCM)

GPIO.setwarnings(False)  # Disable warnings

# Define GPIO pins for TRIG, ECHO, and BUZZER
TRIG = 23  # TRIG connected to GPIO 23
ECHO = 24  # ECHO connected to GPIO 24
BUZZER = 17  # BUZZER connected to GPIO 17

# Set up the GPIO pins as output (TRIG and BUZZER) and input (ECHO)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(BUZZER, GPIO.OUT)

# Define the total height of the bottle (in centimeters)
TOTAL_BOTTLE_HEIGHT = 30  # Replace with actual height of the saline bottle

# ThingSpeak configuration
CHANNEL_ID = "2679920"  # Your ThingSpeak channel ID
API_KEY = "YT1IM7K0MG5T2EJR"  # Your ThingSpeak API Write key
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# Email Configuration
EMAIL_USER = "1675699.dineshkumar@gmail.com"  # Replace with your Gmail address
EMAIL_PASSWORD = "jses ugit ltrd hhkc"  # Replace with your Gmail app password
RECIPIENT_EMAIL = "21bq1a0413@vvit.net"  # Recipient email

# Variable to hold the previous water level to calculate flow rate
previous_level = None
previous_time = None

# Variable to track if saline is currently in use
saline_in_use = False

# Flag to track if an email has been sent during this code execution
email_sent = False

def send_email_alert(saline_level):
    # Create message container - MIME standard
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = "Alert: Saline Level Low"

    # Body of the email
    body = f"Warning: The saline level has dropped below 10 cm. Current level: {saline_level} cm."
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Establish a secure session with Gmail's outgoing SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, text)
        server.quit()
        print(f"Email sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def measure_distance():
    # Ensure the TRIG pin is low
    GPIO.output(TRIG, False)
    time.sleep(2)  # Allow the sensor to settle

    # Trigger the sensor by sending a 10µs high pulse to TRIG
    GPIO.output(TRIG, True)
    time.sleep(0.00001)  # 10 microseconds
    GPIO.output(TRIG, False)

    # Measure the time between sending and receiving the pulse
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    # Calculate the duration of the pulse
    pulse_duration = pulse_end - pulse_start

    # Convert pulse duration to distance (in centimeters)
    distance = pulse_duration * 17150

    # Round the distance to two decimal places
    distance = round(distance, 2)

    return distance

def calculate_flow_rate(current_level):
    global previous_level, previous_time

    # Get the current time
    current_time = time.time()

    # Calculate flow rate if we have a previous level
    if previous_level is not None and previous_time is not None:
        time_diff = current_time - previous_time  # Time difference in seconds
        level_diff = previous_level - current_level  # Saline level difference
        flow_rate = level_diff / time_diff  # Rate of flow in cm/s
    else:
        flow_rate = 0  # Initial flow rate

    # Update the previous level and time for the next calculation
    previous_level = current_level
    previous_time = current_time

    return round(flow_rate, 2)

def send_to_thingspeak(level, flow_rate):
    # Prepare the data to send to ThingSpeak with fields for Saline Level and Flow Rate
    payload = {
        'api_key': API_KEY,
        'field1': level,        # 'field1' corresponds to Saline Level in ThingSpeak
        'field2': flow_rate     # 'field2' corresponds to Saline Flow Rate in ThingSpeak
    }

    # Send the data using a POST request
    try:
        response = requests.post(THINGSPEAK_URL, params=payload)
        if response.status_code == 200:
            print("Data successfully sent to ThingSpeak.")
        else:
            print(f"Failed to send data. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending data to ThingSpeak: {e}")

try:
    while True:
        # Measure the distance from the sensor to the saline surface
        distance_to_surface = measure_distance()

        # Calculate the current saline level
        current_level = TOTAL_BOTTLE_HEIGHT - distance_to_surface

        # Ensure the saline level is non-negative
        if current_level < 0:
            current_level = 0

        print(f"Measured saline level: {current_level} cm")

        # Buzzer logic: Activate buzzer if saline level drops below 10 cm
        if current_level < 10:
            GPIO.output(BUZZER, GPIO.HIGH)  # Turn on the buzzer
            if not email_sent:
                send_email_alert(current_level)  # Trigger email alert
                email_sent = True  # Set the flag to prevent further emails
        else:
            GPIO.output(BUZZER, GPIO.LOW)  # Turn off the buzzer

        # If the saline is in use, prevent level increase
        if saline_in_use:
            if previous_level is not None and current_level > previous_level:
                print("Detected an unrealistic increase in saline level while in use, retaining previous level.")
                current_level = previous_level  # Retain the previous level

        print(f"Current saline level after adjustment: {current_level} cm")

        # Calculate the saline flow rate
        flow_rate = calculate_flow_rate(current_level)

        print(f"Current saline flow rate: {flow_rate} cm/s")

        # Send saline level and flow rate to ThingSpeak
        send_to_thingspeak(current_level, flow_rate)

        # Add a delay between measurements and uploads to ThingSpeak (15s is typical for ThingSpeak)
        time.sleep(15)

        # Check if saline is being used and update saline_in_use as needed
        # This is where you'd implement your logic to determine if saline is in use
        # For demonstration, let's toggle saline_in_use based on some condition (for example, every few iterations)
        saline_in_use = not saline_in_use  # Example toggle; replace with your actual condition

except KeyboardInterrupt:
    print("Measurement stopped by User")
    GPIO.cleanup()
