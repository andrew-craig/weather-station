import bme280
import smbus2
from time import sleep

port = 1
address = 0x76
bus = smbus2.SMBus(port)
calibration_params = bme280.load_calibration_params(bus,address)

def read_all():
    data = bme280.sample(bus, address, calibration_params)
    return data.temperature, data.humidity, data.pressure
