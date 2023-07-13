# Desk-LED-WX-Strip
A WS218112 strip of 30 LEDs connected to a Raspberry Pi Pico W that light up based on the weather for the next hour.
I'm using the free WX API available through https://open-meteo.com/

When the temperature is over a set ammount in the next hour, the left LEDs light up red.

When the rain percentage is over a set ammount in the next hour, the riht LEDs light up blue.

!["In Use"](/images/inuse.jpg)

I'm using the Neopixel library for the Pi Pico from blaz-r

https://github.com/blaz-r/pi_pico_neopixel
