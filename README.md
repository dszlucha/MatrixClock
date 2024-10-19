# MatrixClock
CircuitPython LED matrix clock displays the current time, temperature and weather conditions on a 8 x 32 LED matrix display. Calls [OpenWeather](https://openweathermap.org/api) for temperature, weather conditions and timezone. 

# Parts
* [ESP32-S3](https://a.co/d/bG1RVT6)
* [8 x 32 MAX7219 Dot Matrix Module](https://a.co/d/fJbiUec)

# Dependencies
```sh
circup install adafruit-circuitpython-max7219
circup install adafruit-circuitpython-ntp
circup install adafruit-circuitpython-requests
circup install adafruit_connection_manager
circup install adafruit_httpserver
circup install asyncio
```

# settings.toml
```
# To auto-connect to Wi-Fi
CIRCUITPY_WIFI_SSID="my WiFi SSID"
CIRCUITPY_WIFI_PASSWORD="my WiFi SSID password"

# To enable the web workflow. Change this too!
# Leave the User field blank in the browser.
CIRCUITPY_WEB_API_PASSWORD="passw0rd"

# For openweathermap
LOCATION="my location"
UNITS="imperial"
APIKEY="my API key"
```
