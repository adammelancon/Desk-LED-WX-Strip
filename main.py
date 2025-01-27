#Import external modules
import requests
from neopixel import Neopixel
import time
import ntptime
import machine
import utime
from ssd1306 import SSD1306_I2C
from machine import Pin, I2C
import math
import gc

#Import My Scripts
from wifi import *
from config_secrets import *

#Set to 1 to see debug prints
DEBUG = 1

#============================== HARDWARE SETUP
#SSD1306 Setup
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=400000)
display = SSD1306_I2C(128, 64, i2c)
display.fill(0)
display.show()

#Neopixel Setup
numpix = 30
pixels = Neopixel(numpix, 0, 28, "GRB")


#============================== NEOPIXEL VARIABLES
#LED Colors and Brightness
softwhite = (255, 200, 50)
blue = (0, 0, 255)
red = (255, 0, 0)
off = (0, 0, 0)
BRIGHTNESS = 80

# Set LED Ranges
RAIN_START = 0
RAIN_STOP = 3
LIGHT_START = 4
LIGHT_STOP = 25
HEAT_START =26
HEAT_STOP = 29


#=============================== OPEN METEO WX API VARIABLES
#Weather Triggers
TEMPMAX = 85  #Temp In The Next Hour In Degrees F
RAINMAX = 15  #Rain Chance In The Next Hour In %

#Time between API calls to not abuse it.
API_TIMER = 90

#Open-Meteo API URL
WX_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=30.2241&longitude=-92.0198&hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&timezone=America%2FChicago&forecast_days=1"


#=============================== OLED VARIABLES
# Icon Positions
icon_x = 105
icon_y = 45
rain_x = icon_x - 3
rain_y = icon_y + 10

CLEAR_AREAS = {
    "rain": (0, 35, 80, 10),
    "temp": (0, 20, 80, 10),
    "sat":  (0, 50, 100, 10),
}

#=============================== N2YO API VARIABLES

# N2YO API information
sat_id = 25544    
sat_name = "ISS"
lat = 30.20128
long = -92.04119
elev_in_m = 10
n2yo_url = f"https://api.n2yo.com/rest/v1/satellite/positions/{sat_id}/{lat}/{long}/{elev_in_m}/1?apiKey={n2yo_api_key}"
# Previous Sat Elevation for Calculation
prev_sat_elev = 0
# Define a timer to control the API request frequency
api_request_timer = utime.time()


#============================== OLED UTILITIES
def clear_text_area(area_key):
    if area_key in CLEAR_AREAS:
        x, y, w, h = CLEAR_AREAS[area_key]
        display.fill_rect(x, y, w, h, 0)
        display.show()
    

def clear_icon_area(x, y, width, height, color):
    display.fill_rect(x, y, width, height, color)  # Clear icon area
    display.show()
    
    
#============================== NEOPIXEL LED UTILITIES
def clear_np():
    
    """
    Simple function to turn off all LEDs.
    """
    set_pixels_color(0, 29, off)
    
    
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
    
    
def set_pixels_color(start_index, end_index, color):
    
    """
    Set the color of pixels within the specified index range.
    """
    for i in range(start_index, end_index+1):
        pixels[i] = color
    

#============================== SATELLITE UTILITIES
def get_satellite_coordinates():
    
    """
    Gets satellite data from n2yo API
    """
    
    global prev_sat_elev

    print(n2yo_url)
    try:
        response = requests.get(n2yo_url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                elevation = data["positions"][0]["elevation"]
                gc.collect()  # Free memory after processing the response
                if elevation > prev_sat_elev:
                    print("The elevation is rising.")
                    print(f"{sat_name} {elevation}")
                    clear_text_area("sat")
                    display.text(f"{sat_name} {elevation} U", 0, 50, 1)
                    display.show()
                elif elevation < prev_sat_elev:
                    print("The elevation is descending.")
                    print(f"{sat_name} {elevation}")
                    clear_text_area("sat")
                    display.text(f"{sat_name} {elevation} D", 0, 50, 1)
                    display.show()
                else:
                    print("The elevation is unchanged.")
                    print(f"{sat_name} {elevation}")
                
                prev_sat_elev = elevation
            except ValueError:
                print("Error decoding JSON response.")
                print("Response content:", response.content)
        else:
            print(f"Error: Received status code {response.status_code}")
            if response.status_code == 404:
                print("Resource not found.")
            elif response.status_code == 500:
                print("Server error occurred.")
            else:
                print(f"Unexpected status code: {response.status_code}")
    except OSError as e:
        # Handle request-related errors (network issues, timeouts, etc.)
        print(f"Request failed: {e}")
    
    
#============================== CLOCK UTILITIES
def clock_set():
    
    """
    Sets the internal clock.
    """
    # Set the RTC time using ntptime
    try:
        ntptime.settime()
    except OSError as e:
        print("Error setting RTC time:", e)
        return

    # Adjust RTC time for Central Daylight Saving Time (CDT)
    rtc = machine.RTC()
    current_time = utime.localtime()  # This is now UTC
    rtc_time = rtc.datetime()
    
    # Determine time zone offset (CDT: UTC-5, CST: UTC-6)
    year, month, day, hour, minute, second, weekday, yearday = current_time
    if (month > 3 and month < 11) or (month == 3 and day >= 14) or (month == 11 and day < 7):
        offset = -5  # CDT (Daylight Saving Time)
    else:
        offset = -6  # CST (Standard Time)
    
    #print(f"rtc.datetime = {rtc_time}")
    #print(f"utime.localtime = {current_time}")
    
    # Adjust for time zone
    local_hour = (hour + offset) % 24

    # Build local time tuple for rtc.datetime()
    local_time = (
        year,          # year
        month,         # month
        day,           # day
        weekday,       # weekday (0 = Monday, 6 = Sunday)
        local_hour,    # hour
        minute,        # minute
        second,        # second
        0,             # microsecond (not used)
    )
    
    # Set RTC to local time
    try:
        rtc.datetime(local_time)
    except OSError as e:
        print("Error setting RTC datetime:", e)
        return    
    print("UTC time:", current_time)
    print("Local time:", rtc.datetime())
    return


def get_hour():
    
    """
    Sets a varialbe with the local hour number to read the correct forecast time.
    """
    rtc = machine.RTC()
    return rtc.datetime()[4]


def display_time(hour, minutes):
    
    """
    Print time on OLED Display
    """
    
    display.fill_rect(85, 8, 40, 10, 0)  # x, y, width, height, color (0=black)
    if minutes <= 10:
        display.text(f"{to_12_hour_format(hour)}:0{minutes}", 85, 8, 1)
    else:
        display.text(f"{to_12_hour_format(hour)}:{minutes}", 85, 8, 1)
    display.show()


def to_12_hour_format(hour):
    
    """
    Converts a given hour from 24-hour format to 12-hour format.
    """
    if hour == 0:
        return (12)  # Midnight case
    elif hour < 12:
        return (hour)
    elif hour == 12:
        return (12)  # Noon case
    else:
        return (hour - 12)


#============================== OLED ICONS
def draw_icon(icon_type, x_center, y_center):
    
    """
    Draws the icons.
    """
    
    if icon_type == "sun":
        radius = 10
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                if x*x + y*y <= radius*radius:
                    display.pixel(x_center + x, y_center + y, 1)
        for d in range(0, 360, 30):
            x = int(radius * 1.5 * math.cos(math.radians(d)))
            y = int(radius * 1.5 * math.sin(math.radians(d)))
            display.line(x_center, y_center, x_center + x, y_center + y, 1)
    elif icon_type == "rain":
        radius = 5
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                if x*x + y*y <= radius*radius:
                    display.pixel(x_center + x, y_center + y, 1)
        radius = 7
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                if x*x + y*y <= radius*radius:
                    display.pixel(x_center + x + 8, y_center + y - 2, 1)
        radius = 5
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                if x*x + y*y <= radius*radius:
                    display.pixel(x_center + x + 16, y_center + y, 1)
        draw_diagonal_lines(x_center - 3, y_center + 10, 3, 5, 4)


def draw_diagonal_lines(x_start, y_start, length, spacing, count):
    
    """
    Draws the rain lines.
    """
    current_y_start = y_start
    for i in range(count):
        x_end = x_start + length
        y_end = current_y_start - length
        display.line(x_start, current_y_start, x_end, y_end, 1)
        x_start += spacing  # Move the starting x to the right for the next line


#============================== WEATHER UTILITIES
def get_weather_data():
    
    """
    Make a request to the Open-Meteo API to get the current weather condition.
    """
    try:
        response = requests.get(WX_API_URL)
        if response.status_code == 200:
            data = response.json()
            gc.collect()  # Free memory after processing the response
            # Check if the keys exist
            if "hourly" not in data or "temperature_2m" not in data["hourly"]:
                print("Unexpected weather data structure.")
                return None
            return data
        else:
            print(f"Weather API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Weather API request failed: {e}")
        return None


def check_temperature(weather_data):
    
    """
    Checks if the temperature is over the threshold.
    """
    temperature_next_hour = weather_data["hourly"]["temperature_2m"][get_hour()]
    print(f"Checking if temp is over {TEMPMAX} degrees")
    print(f"Temp Next Hour: {temperature_next_hour}")

    clear_text_area("temp")
    display.text(f"Temp: {int(temperature_next_hour)} f", 0, 20, 1)
    display.show()
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
    if chance_of_rain == 0:
        clear_text_area("rain")
        display.text(f"Rain: 0%", 0, 35, 1)
        clear_icon_area(icon_x - 10, icon_y - 10, 40, 40, 0)
        draw_icon("sun",icon_x,icon_y)
        display.show()
    else:
        clear_text_area("rain")
        display.text(f"Rain: {chance_of_rain}%", 0, 35, 1)
        clear_icon_area(icon_x - 10, icon_y - 10, 40, 40, 0)
        draw_icon("rain",icon_x,icon_y)
        display.show()

        
    if chance_of_rain > RAINMAX:
        return True
    else:
        return False
    
#============================== WIFI UTILS

def connect_to_wifi_with_retry(retries=3):
    for attempt in range(retries):
        if connect_to_wifi_networks():
            return True
        print(f"Wi-Fi connection failed, retrying ({attempt + 1}/{retries})")
        time.sleep(5)
    return False


#============================== MAIN LOOP AND WIFI CHECK
def main_loop():
    
    """
    Main program loop.
    """
    
    # Add access to write the 'global' API timer
    global api_request_timer
    
    last_minute = -1
    
    # Checking Sats...
    display.text(f"ACQ ISS POS", 0, 50, 1)
    display.show()
    
    while True:
        try:
            # Check if the timer has elapsed to make an API request
            current_time = utime.time()
            
            #Update the clock on the minute
            rtc = machine.RTC()
            _, _, _, _, hour, minute, _, _ = rtc.datetime()
            if minute != last_minute:
                display_time(hour, minute)
                last_minute = minute
            
            if DEBUG == 1:
                #print(f"Current time = {current_time}")
                pass
            
            if current_time - api_request_timer >= API_TIMER:
                
                print("-------------------------")
                print(f"Current Hour: {get_hour()}:00")
                
                # Make a request to the Open-Meteo API to get the current weather condition
                
                weather_data = get_weather_data()
                if DEBUG == 1:
                    print(weather_data)
                if weather_data is not None:
                    set_leds(weather_data)
                    pixels.brightness(BRIGHTNESS)
                    pixels.show()
                else:
                    print("Skipping LED update due to invalid weather_data.")

                # Set the brightness and show the updated colors on the NeoPixel strip

                get_satellite_coordinates()
                
                # Reset the API timer
                api_request_timer = current_time
                print(f"Elapsed Time: {current_time - api_request_timer}")
                
                gc.collect()  # Free memory after processing
                
        except OSError as e:
            #Error handling for API errors.
            print("API request error:", e)

        # Program delay, just because.
        time.sleep(.1)


# Run program if connected to Wi-Fi network
if connect_to_wifi_with_retry(3):
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



