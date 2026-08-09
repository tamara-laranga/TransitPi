import gc
import network
import time
import urequests
from machine import Pin, I2C
from machine_i2c_lcd import I2cLcd
from secrets import WIFI_SSID, WIFI_PASSWORD, EMT_EMAIL, EMT_PASSWORD

STOP_ID = 0  # add requested stop
LINE = 0  # add requested LINE
API = "https://openapi.emtmadrid.es"

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)
led = Pin("LED", Pin.OUT)


def lcd_write(line1, line2):
    lcd.clear()
    lcd.move_to(0, 0)
    lcd.putstr(line1[:16])
    lcd.move_to(0, 1)
    lcd.putstr(line2[:16])


def connect_wifi(tries=5):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    for attempt in range(tries):
        if wlan.isconnected():
            return True
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(15):
            if wlan.isconnected():
                return True
            time.sleep(1)
    return wlan.isconnected()


def get_token(tries=3):
    url = API + "/v1/mobilitylabs/user/login/"
    headers = {"email": EMT_EMAIL, "password": EMT_PASSWORD}
    for attempt in range(tries):
        try:
            gc.collect()
            r = urequests.get(url, headers=headers)
            d = r.json()
            r.close()
            try:
                return d["data"][0]["accessToken"]
            except (KeyError, IndexError, TypeError):
                return None
        except Exception:
            time.sleep(2)
    return None


def get_arrivals(token):
    gc.collect()
    url = API + "/v2/transport/busemtmad/stops/{}/arrives/{}/".format(STOP_ID, LINE)
    headers = {"accessToken": token}
    body = {
        "cultureInfo": "ES",
        "Text_StopRequired_YN": "Y",
        "Text_EstimationsRequired_YN": "Y",
        "Text_IncidencesRequired_YN": "N",
        "DateTime_Referenced_Incidencies_YYYYMMDD": "",
    }
    r = urequests.post(url, headers=headers, json=body)
    d = r.json()
    r.close()
    return d


def minutes_label(secs):
    if secs is None or secs < 0:
        return "--"
    if secs >= 999999 or secs > 3600:
        return "--"
    if secs <= 20:
        return "YA"
    m = secs // 60
    s = secs % 60
    return "{:>2}m {:02}s".format(m, s)


def refresh(token):
    for attempt in range(3):
        try:
            d = get_arrivals(token)
            arrivals = d.get("data", [{}])[0].get("Arrive", [])
            buses = [a for a in arrivals if str(a.get("line")) == LINE]
            if not buses:
                lcd_write("Bus ".format(LINE), "timings not available")
                return token
            t1 = minutes_label(buses[0].get("estimateArrive"))
            t2 = (
                minutes_label(buses[1].get("estimateArrive"))
                if len(buses) > 1
                else "--"
            )
            dest = buses[0].get("destination", "")[:11]
            lcd_write("Bus{} {}".format(LINE, dest), "1:{} 2:{}".format(t1, t2))
            return token
        except Exception:
            time.sleep(2)
    lcd_write("Error connecting to transport API", "re-try...")
    return None


def main():
    led.on()
    lcd_write("Connecting WiFi", "...")
    if not connect_wifi():
        lcd_write("WiFi error", "check router")
        return

    lcd_write("WiFi OK", "login API...")
    token = None
    while True:
        try:
            if token is None:
                token = get_token()
                if token is None:
                    lcd_write("API login", "error")
                    time.sleep(20)
                    continue
            token = refresh(token)
            if token is None:
                time.sleep(20)
                continue
        except Exception as e:
            lcd_write("Error", str(e)[:16])
        led.toggle()
        time.sleep(30)


if __name__ == "__main__":
    main()
