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

async def get_open_weather() -> bool:
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
            last_weather = time.time()
        except:
            pass

        conditions = weather_data['weather'][0]['main']

        if conditions == 'Thunderstorm':
            conditions = 'Thndrstm'
        elif conditions == 'Atmosphere':
            conditions = 'Atmosphr'

        temperature = weather_data['main']['temp']
        timezone = weather_data['timezone']
        await asyncio.sleep(300)

async def get_ntp_time() -> bool:
    """Set time from NTP"""
    global last_ntp
    while True:
        try:
            ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=timezone/3600, cache_seconds=3600)
            rtc.RTC().datetime = ntp.datetime
            last_ntp = time.time()
        except:
            pass
        
        await asyncio.sleep(86400) 

def get_formatted_time(epoch: float) -> str:
    """Returns formatted time given an epoch"""
    tm = time.localtime(epoch)
    return f'{tm.tm_year}-{tm.tm_mon:02}-{tm.tm_mday:02} {tm.tm_hour:02}:{tm.tm_min:02}:{tm.tm_sec:02}'

def get_uptime(uptime: float) -> str:
    """Compute uptime given number of seconds"""
    days = int(uptime / 86400)
    hours = int((uptime - (days * 86400)) / 3600)
    minutes = int((uptime - (days * 86400) - (hours * 3600)) / 60)
    seconds = int((uptime - (days * 86400) - (hours * 3600) - (minutes * 60)))
    return f'{days} days, {hours} hours, {minutes} minutes, {seconds} seconds'

def display_time(show_colon: bool=True):
    """Display the time"""
    hour = (time.localtime().tm_hour + 11) % 12 + 1
    minute = time.localtime().tm_min
    matrix.clear_all()
    if show_colon:
        matrix.text("{:>2}".format(hour) + ":{:02d}".format(minute), 0, 0)
    else:
        matrix.text("{:>2}".format(hour) + " {:02d}".format(minute), 0, 0)  
    matrix.show()

async def update_display():
    """Cycle through time, temperature and conditions"""
    while True:
        # display time

        display_time()
        await asyncio.sleep(1)
        
        display_time(False)
        await asyncio.sleep(1)

        display_time()
        await asyncio.sleep(1)

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
        server.poll()
        await asyncio.sleep(0)

async def main():
    """Main entry point"""

    weather_task = asyncio.create_task(get_open_weather())
    ntp_task = asyncio.create_task(get_ntp_time())
    display_task = asyncio.create_task(update_display())
    http_task = asyncio.create_task(handle_http_requests())
    await asyncio.gather(weather_task, ntp_task, display_task, http_task)

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
server = Server(pool, debug=True)

@server.route("/")
def base(request: Request) -> Response:
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
    info += f'<tr><td>Current time:</td><td>{get_formatted_time(time.time())}</td></tr>'
    info += f'<tr><td>Last NTP:</td><td>{get_formatted_time(last_ntp)}</td></tr>'
    info += f'<tr><td>System uptime:</td><td>{get_uptime(time.monotonic())}</td></tr>'
    info += f'<tr><td>Program uptime:</td><td>{get_uptime(time.monotonic() - program_uptime)}</td></tr>'
    info += f'<tr><td>Heap alloc:</td><td>{round(gc.mem_alloc()/1024)} kb</td></tr>'
    info += f'<tr><td>Heap free:</td><td>{round(gc.mem_free()/1024)} kb</td></tr>'
    info += f'<tr><td>Location:</td><td>{location}</td></tr>'
    info += f'<tr><td>Last OpenWeather:</td><td>{get_formatted_time(last_weather)}</td></tr>'
    info += '<tr><td>OpenWeather data:</td><td>'
    info += str(weather_data)
    info += '</td></tr></table>'
    return Response(request, body=info, content_type='text/html')

server.start(str(wifi.radio.ipv4_address))

asyncio.run(main())
