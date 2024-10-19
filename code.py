# Built in libraries
import board
import busio
import digitalio
import gc
import microcontroller
import os
import rtc
import socketpool
import sys
import time
import wifi

# External libraries
import adafruit_connection_manager
from adafruit_httpserver import Server, Request, Response
from adafruit_max7219 import matrices
import adafruit_ntp
import adafruit_requests
import asyncio

async def getOpenWeather(run_once = False):
    """Get weather data including timezone"""
    global conditions
    global last_weather
    global temperature
    global timezone
    global weather_data
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&units={units}&appid={apikey}"

    while True:
        try:      
            with requests.get(url) as response:
                weather_data = response.json()
        except:
            if run_once:
                return False

        last_weather = time.time()

        conditions = weather_data['weather'][0]['main']

        if conditions == 'Thunderstorm':
            conditions = 'Thndrstm'
        elif conditions == 'Atmosphere':
            conditions = 'Atmosphr'

        temperature = weather_data['main']['temp']
        timezone = weather_data['timezone']
        if run_once:
            break
        await asyncio.sleep(300)

    return True

async def GetNTPTime(run_once = False):
    """Set time from NTP"""
    global last_ntp
    while True:
        try:
            ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=timezone/3600, cache_seconds=3600)
        except:
            if run_once:
                return False
        
        rtc.RTC().datetime = ntp.datetime
        last_ntp = time.time()
        if run_once:
            break
        await asyncio.sleep(86400) 

    return True

def getFormattedTime(epoch):
    """Returns formatted time given an epoch"""
    tm = time.localtime(epoch)
    return f'{tm.tm_year}-{tm.tm_mon:02}-{tm.tm_mday:02} {tm.tm_hour:02}:{tm.tm_min:02}:{tm.tm_sec:02}'

def getUptime(uptime):
    """Compute uptime given number of seconds"""
    days = int(uptime / 86400)
    hours = int((uptime - (days * 86400)) / 3600)
    minutes = int((uptime - (days * 86400) - (hours * 3600)) / 60)
    seconds = int((uptime - (days * 86400) - (hours * 3600) - (minutes * 60)))
    return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'

async def display():
    """Cycle through time, temperature and conditions"""
    while True:
        # display time
        hour = (time.localtime().tm_hour + 11) % 12 + 1
        minute = time.localtime().tm_min
        matrix.clear_all()
        matrix.text("{:>2}".format(hour) + ":{:02d}".format(minute), 0, 0)
        matrix.show()
        await asyncio.sleep(3)

        # display temperature
        matrix.clear_all()
        matrix.text("{:4.0f}".format(temperature), 0, 0)
        matrix.show()
        await asyncio.sleep(3)

        # display conditions
        matrix.clear_all()
        matrix.text(conditions, 0, 1, font_name = "font3x8.bin")
        matrix.show()
        await asyncio.sleep(3)

async def handle_http_requests():
    """Run the web server"""
    while True:
        # Process any waiting requests
        pool_result = server.poll()
        await asyncio.sleep(0)

async def main():
    """Main entry point"""
    await asyncio.gather(getOpenWeather(), GetNTPTime(), display(), handle_http_requests())

# setup
program_uptime = time.monotonic()

# wiring:
# pin 1 5V
# pin 2 GND 
# pin 5 GPIO2 DIN
# pin 7 GPIO4 CLK
# pin 9 GPIO6 CS

spi = busio.SPI(board.IO4, board.IO2)
cs = digitalio.DigitalInOut(board.IO6)

matrix = matrices.CustomMatrix(spi, cs, 32, 8)
matrix.brightness(0)

# get settings for openweathermap
location = os.getenv("LOCATION")
units = os.getenv("UNITS")
apikey = os.getenv("APIKEY")

pool = socketpool.SocketPool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)
server = Server(pool, "/static", debug=True)

@server.route("/")
def base(request: Request):
    info = """
<style>
table {
  border-collapse: collapse;
  width: 100%;
}

th, td {
  text-align: left;
  padding: 8px;
}

tr:nth-child(even) {
  background-color: #D6EEEE;
}
</style>"""
    info += f'<table><tr><td>System:</td><td>{sys.implementation._machine}</td></tr>'
    info += f'<tr><td>Version:</td><td>{sys.version}</td></tr>'
    info += f'<tr><td>Temperature:</td><td>{microcontroller.cpu.temperature} deg C</td></tr>'
    info += f'<tr><td>Frequency:</td><td>{microcontroller.cpu.frequency/1000000} MHz</td></tr>'
    info += f'<tr><td>Reset reason:</td><td>{microcontroller.cpu.reset_reason}</td></tr>'
    info += f'<tr><td>Hostname:</td><td>{wifi.radio.hostname}</td></tr>'
    info += f'<tr><td>Channel:</td><td>{wifi.radio.ap_info.channel}</td></tr>'
    info += f'<tr><td>Power:</td><td>{wifi.radio.tx_power} dBm</td></tr>'
    info += f'<tr><td>RSSI:</td><td>{wifi.radio.ap_info.rssi} dBm</td></tr>'
    info += f'<tr><td>Current time:</td><td>{getFormattedTime(time.time())}</td></tr>'
    info += f'<tr><td>Last NTP:</td><td>{getFormattedTime(last_ntp)}</td></tr>'
    info += f'<tr><td>System uptime:</td><td>{getUptime(time.monotonic())}</td></tr>'
    info += f'<tr><td>Program uptime:</td><td>{getUptime(time.monotonic() - program_uptime)}</td></tr>'
    info += f'<tr><td>Heap alloc:</td><td>{round(gc.mem_alloc()/1024)} kb</td></tr>'
    info += f'<tr><td>Heap free:</td><td>{round(gc.mem_free()/1024)} kb</td></tr>'
    info += f'<tr><td>Location:</td><td>{location}</td></tr>'
    info += f'<tr><td>Last OpenWeather:</td><td>{getFormattedTime(last_weather)}</td></tr>'
    info += '<tr><td>OpenWeather data:</td><td>'
    info += str(weather_data)
    info += '</td></tr></table>'
    return Response(request, info, content_type='text/html')

server.start(str(wifi.radio.ipv4_address))

# get weather data including timezone
if getOpenWeather(run_once=True) == False:
    matrix.clear_all()
    matrix.text('W error', 0, 1, font_name = "font3x8.bin")
    matrix.show()
    time.sleep(60)
    import supervisor
    supervisor.reload()

if GetNTPTime(run_once=True) == False:
    matrix.clear_all()
    matrix.text('T error', 0, 0)
    matrix.show()
    time.sleep(60)
    import supervisor
    supervisor.reload() 

asyncio.run(main())
