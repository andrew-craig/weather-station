from pms5003 import PMS5003

pms5003 = PMS5003(device="/dev/serial0", baudrate=9600, pin_enable="GPIO22", pin_reset="GPIO27")

def read_all():
    data = pms5003.read()
    return data
