import time

time.sleep(2)

try:
    import bus_times

    bus_times.main()
except Exception as e:
    from machine import Pin
    import time as t

    led = Pin("LED", Pin.OUT)
    while True:
        led.toggle()
        t.sleep(0.5)
