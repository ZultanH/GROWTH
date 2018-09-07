import pyowm
import requests

JWT_SECRET = ''
owm = pyowm.OWM('')

def getIP():
    r = requests.get("http://api.ipify.org/")
    ip = r.text
    return ip

def locationData():
    ip = getIP()
    url = "https://tools.keycdn.com/geo.json?host=%s" % ip
    r = requests.get(url)
    json = r.json()
    return json['data']['geo']['city'] + ',' + json['data']['geo']['region_code']

def getWeather(short):
    location_str = locationData()
    observation = owm.weather_at_place(location_str)
    w = observation.get_weather()
    if short:
        return {
            "wind": w.get_wind(),
            "humidity": w.get_humidity(),
            "temperature": w.get_temperature("celsius")
        }
    else:
        return {
            "clouds": w.get_clouds(),
            "rain": w.get_rain(),
            "snow": w.get_snow(),
            "wind": w.get_wind(),
            "humidity": w.get_humidity(),
            "pressure": w.get_pressure(),
            "temperature": w.get_temperature(),
            "status": w.get_status(),
            "detailed_status": w.get_detailed_status(),
            "sunrise_time": w.get_sunset_time('iso')
        }
