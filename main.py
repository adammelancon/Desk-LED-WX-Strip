#Import external modules
import urequests as requests
from neopixel import Neopixel
import time
import ntptime
import machine
import utime

#Import My Scripts
from wifi import *
from config_secrets import *

#Neopixel Setup
numpix = 30
pixels = Neopixel(numpix, 0, 28, "GRB")

#LED Colors and Brightness
softwhite = (255, 200, 50)
blue = (0, 0, 255)
red = (255, 0, 0)
off = (0, 0, 0)
BRIGHTNESS = 50

# Set LED Ranges
RAIN_START = 0
RAIN_STOP = 3
LIGHT_START = 4
LIGHT_STOP = 25
HEAT_START =26
HEAT_STOP = 29

#Weather Triggers
TEMPMAX = 80  #Temp In The Next Hour In Degrees F
RAINMAX = 10  #Rain Chance In The Next Hour In %

#Set to 1 to see debug prints
DEBUG = 0

#Time between API calls to not abuse it.
API_TIMER = 30

# Define a timer to control the API request frequency
api_request_timer = utime.time()

#Open-Meteo API URL
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=30.2241&longitude=-92.0198&hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&timezone=America%2FChicago&forecast_days=1"


def set_pixels_color(start_index, end_index, color):
    """
    Set the color of pixels within the specified index range.
    """
    for i in range(start_index, end_index+1):
        pixels[i] = color
        

def get_hour():
    """
    Sets a varialbe with the local hour number to read the correct forecast time.
    """
    rtc = machine.RTC()
    current_time = rtc.datetime()
    
    current_hour = current_time[4]
    if DEBUG == 1:
        print(f"Unadjusted Hour = {current_hour}")
    if current_hour == 0:
        current_hour = 19
    elif current_hour == 1:
        current_hour = 20
    elif current_hour == 2:
        current_hour = 21
    elif current_hour == 3:
        current_hour = 22
    elif current_hour == 4:
        current_hour = 23
    else:
        current_hour = current_time[4] -5
    
    if DEBUG == 1:
        print(f"Adjusted Hour: {current_hour}")
    return current_hour


def clock_set():
    """
    Sets the internal clock.
    """
    # Set the RTC time using ntptime
    try:
        ntptime.settime()
    except OSError as e:
        print("Error setting RTC time:", e)

    # Adjust RTC time for Central Daylight Saving Time (CDT)
    rtc = machine.RTC()
    current_time = rtc.datetime()

    # Get the current month and day
    month = current_time[1]
    day = current_time[2]

    # Check if the current date is within the Central Daylight Saving Time period (second Sunday of March to first Sunday of November)
    if (month > 3 and month < 11) or (month == 3 and (day - current_time[6]) >= 8 - current_time[3]) or (month == 11 and (day - current_time[6]) < 1 - current_time[3]):
        # Adjust the RTC time by adding 1 hour
        rtc.datetime((current_time[0], current_time[1], current_time[2], current_time[3] + 1, current_time[4], current_time[5], current_time[6], current_time[7]))

    # Convert RTC time to local time (UTC-5 for Central Daylight Saving Time)
    current_time = rtc.datetime()
    local_time = (current_time[0], current_time[1], current_time[2], current_time[3] - 5, current_time[4], current_time[5], current_time[6], current_time[7])
    rtc.datetime(local_time)
    if DEBUG == 1:
        print(f"Raw Date: {rtc.datetime()}")
        

def clear_np():
    """
    Simple function to turn off all LEDs.
    """
    set_pixels_color(0, 29, off)
    
    
def get_weather_data():
    """
    Make a request to the Open-Meteo API to get the current weather condition.
    """
    response = requests.get(API_URL)
    weather_data = response.json()
    return weather_data


def check_temperature(weather_data):
    """
    Checks if the temperature is over the threshold.
    """
    temperature_next_hour = weather_data["hourly"]["temperature_2m"][get_hour()]
    print(f"Checking if temp is over {TEMPMAX} degrees")
    print(f"Temp Next Hour: {temperature_next_hour}")
    if temperature_next_hour > TEMPMAX:
        return True
    else:
        return False


def check_rain_chance(weather_data):
    """
    Checks if the chance of rain is over the threshold.
    """
    chance_of_rain = weather_data["hourly"]["precipitation_probability"][get_hour()]
    print(f"Checking if rain is over {RAINMAX}%")
    print(f"Rain Chance Next Hour: {chance_of_rain}")
    if chance_of_rain > RAINMAX:
        return True
    else:
        return False


def set_leds(weather_data):
    """
    Sets the LEDs based on the weather conditions.
    """
    if check_temperature(weather_data):
        # Set pixels 27-29 to red
        set_pixels_color(HEAT_START, HEAT_STOP, (red))
    else:
        # Set pixels 27-29 to soft white
        set_pixels_color(HEAT_START, HEAT_STOP, softwhite)

    if check_rain_chance(weather_data):
        # Set pixels 0-10 to blue
        set_pixels_color(RAIN_START, RAIN_STOP, blue)
    else:
        # Set pixels 0-10 to soft white
        set_pixels_color(RAIN_START, RAIN_STOP, softwhite)

    # Set remaining pixels to soft white
    set_pixels_color(LIGHT_START, LIGHT_STOP, softwhite)


def main_loop():
    """
    Main program loop.
    """
    
    # Add access to write the 'global' API timer
    global api_request_timer  
    
    while True:
        try:
            # Check if the timer has elapsed to make an API request
            current_time = utime.time()
            
            if DEBUG == 1:
                print(current_time)
            
            
            if current_time - api_request_timer >= API_TIMER:
                
                print("-------------------------")
                print(f"Current Hour: {get_hour()}:00")
                
                # Make a request to the Open-Meteo API to get the current weather condition
                weather_data = get_weather_data()
                if DEBUG == 1:
                    print(weather_data)
                
                # Set the brightness and show the updated colors on the NeoPixel strip
                set_leds(weather_data)
                pixels.brightness(BRIGHTNESS)
                pixels.show()
                
                # Reset the API timer
                api_request_timer = current_time

        except OSError as e:
            #Error handling for API errors.
            print("API request error:", e)

        # Program delay, just because.
        time.sleep(.1)


# Run program if connected to Wi-Fi network
if connect_to_wifi_networks():
    #Turn off LEDs
    clear_np()
    #Set Clock
    clock_set()
    #Set LED Brightness
    pixels.brightness(BRIGHTNESS)
    #Initial Startup LEDs
    set_pixels_color(12, 16, softwhite)
    pixels.show()
    #Run Main Program Loop
    main_loop()
else:
    print('No Wi-Fi networks available')

