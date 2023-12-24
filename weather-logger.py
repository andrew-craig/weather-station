import sensors.bme_sensor
import sensors.pms_sensor
import time
import os
import asyncio
import datetime
import sqlite3
from uuid_extensions import uuid7str
from zoneinfo import ZoneInfo

def log_readings():

    while True:
        start_time = datetime.datetime.now(tz=ZoneInfo('UTC'))

        # fetch sensor data
        bme_data = sensors.bme_sensor.read_all()
        pms_data = sensors.pms_sensor.read_all()

        # save to database
        database = 'weather-readings.db'
        table_name = 'readings'
        columns = 'id text, ts integer, temperature real, humidity real, pressure real, pm_1 real, pm_2_5 real, pm_10 real'
        connection = sqlite3.connect(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db'), database))
        cursor = connection.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS {table_name} ({columns})""".format(table_name=table_name, columns=columns))
        cursor.execute('INSERT INTO {table_name} VALUES(?, ?, ?, ?, ?, ?, ?, ?)'.format(table_name=table_name),
            [uuid7str(), start_time.timestamp(), bme_data[0], bme_data[1], bme_data[2], pms_data.pm_ug_per_m3(1.0), pms_data.pm_ug_per_m3(2.5), pms_data.pm_ug_per_m3(10)]
            )
        connection.commit()
        connection.close()

        print("Temp: {temp:.1f}°C".format(temp=bme_data[0]))
        print("Air Quality (pm2.5): {pm2_5}".format(pm2_5=pms_data.pm_ug_per_m3(2.5)))

	# calculate how long to wait
        finish_time = datetime.datetime.now(tz=ZoneInfo('UTC'))
        calc_time = (finish_time - start_time).total_seconds()
        time.sleep(max(0, 60 - calc_time))

    return None

def main():
    async def readingsWorker():
        while True:
            log_readings()

#    async def secondWorker():
#        while True:
#            await asyncio.sleep(1)
#            print("Second Worker Executed")


    loop = asyncio.get_event_loop()
    print("Starting Server")
    try:
        asyncio.ensure_future(readingsWorker())
#        asyncio.ensure_future(secondWorker())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping Server")
        loop.close()


if __name__ == "__main__":
    main() 

