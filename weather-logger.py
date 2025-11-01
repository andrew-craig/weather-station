import sensors.bme_sensor
import sensors.pms_sensor
import time
import os
import asyncio
import datetime
import json
import time
import uuid
import logging
import requests
import socket
import sqlite3
import paho.mqtt.client as mqtt
from uuid_extensions import uuid7str
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Database configuration
LOGGER_DB = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "db/weather-logger.db"
)


def initiate_tables(db_path):
    tables = [
        {
            "name": "thp_readings",
            "columns": "id text, ts integer, temperature real, humidity real, pressure real",
        },
        {
            "name": "air_quality_readings",
            "columns": "id text, ts integer, pm1 real, pm2_5 real, pm10 real",
        },
    ]
    logger.info(f"Initiating {len(tables)} tables.")
    print("Initiating tables")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    for table in tables:
        print("Initiating a table")
        print(table.get("name"))
        print(table.get("columns"))
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS {table_name} ({columns})""".format(
                table_name=table.get("name"), columns=table.get("columns")
            )
        )
    connection.commit()
    connection.close()
    print("Completed table initiation")
    logger.info(f"Completed table initiation.")
    return True


def write_logger_data(query):
    connection = sqlite3.connect(LOGGER_DB)
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    connection.close()
    return True


def write_latest_weather(
    id: str, ts: float, temperature: float, humidity: float, pressure: float
):
    query = f"""INSERT INTO thp_readings VALUES('{id}', {ts}, {temperature}, {humidity}, {pressure})"""
    print(query)
    write_logger_data(query)
    return True


def write_latest_air(id: str, ts: float, pm1: float, pm2_5: float, pm10: float):
    query = f"""INSERT INTO air_quality_readings VALUES('{id}', {ts}, {pm1}, {pm2_5}, {pm10})"""
    write_logger_data(query)
    return True


# MQTT broker settings
BROKER_HOST = "hub.local"  # Change to your MQTT broker address
BROKER_PORT = 1883  # Default MQTT port
TOPIC = "outside/weather"  # Change to your desired topic
CLIENT_ID = f"weather-mqtt-{uuid.uuid4()}"  # Generate a unique client ID

# HomeAssistant MQTT configuration
DISCOVERY_PREFIX = "homeassistant"  # Default HomeAssistant discovery prefix
DEVICE_ID = "environment_sensor_1"  # Unique identifier for your device
NODE_ID = socket.gethostname()  # Use hostname as node identifier


def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker"""
    if rc == 0:
        print(f"Connected to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
    else:
        print(f"Failed to connect to MQTT broker. Return code: {rc}")


def on_publish(client, userdata, mid):
    """Callback for when a message is published"""
    print(f"Message ID {mid} published successfully")


def publish_discovery_messages(client):
    """Publish HomeAssistant MQTT discovery messages for each sensor"""
    sensors = {
        "temperature": {
            "name": "Temperature",
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "value_template": "{{ value_json.temperature }}",
        },
        "humidity": {
            "name": "Humidity",
            "unit_of_measurement": "%",
            "device_class": "humidity",
            "state_class": "measurement",
            "value_template": "{{ value_json.humidity }}",
        },
        "pressure": {
            "name": "Pressure",
            "unit_of_measurement": "hPa",
            "device_class": "pressure",
            "state_class": "measurement",
            "value_template": "{{ value_json.pressure }}",
        },
    }

    # Device info (shared across all sensors)
    device_info = {
        "identifiers": [DEVICE_ID],
        "name": f"Environment Sensor {DEVICE_ID}",
        "model": "Custom Sensor Array",
        "manufacturer": "DIY Project",
        "sw_version": "1.0.0",
    }

    # Publish discovery configuration for each sensor
    for sensor_type, config in sensors.items():
        # Config topic: homeassistant/sensor/[device_id]/[sensor_type]/config
        config_topic = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/{sensor_type}/config"

        # Build the config payload
        payload = {
            "name": config["name"],
            "unique_id": f"{DEVICE_ID}_{sensor_type}",
            "device_class": config["device_class"],
            "state_class": config["state_class"],
            "unit_of_measurement": config["unit_of_measurement"],
            "state_topic": f"homeassistant/sensor/{DEVICE_ID}/state",
            "value_template": config["value_template"],
            "device": device_info,
            "availability_topic": f"homeassistant/sensor/{DEVICE_ID}/availability",
            "payload_available": "online",
            "payload_not_available": "offline",
        }

        # Publish discovery message with retain flag
        client.publish(config_topic, json.dumps(payload), qos=1, retain=True)
        print(f"Published discovery message for {sensor_type} sensor")

    # Set device as available
    client.publish(
        f"homeassistant/sensor/{DEVICE_ID}/availability", "online", qos=1, retain=True
    )


def log_readings(mqtt_client):
    while True:
        start_time = datetime.datetime.now(tz=ZoneInfo("UTC"))
        run_uuid = uuid7str()

        # fetch temp data
        try:
            bme_data = sensors.bme_sensor.read_all()
            try:
                payload = {
                    "id": run_uuid,
                    "ts": start_time.timestamp(),
                    "temperature": bme_data[0],
                    "humidity": bme_data[1],
                    "pressure": bme_data[2],
                }
                # Write to local database
                write_latest_weather(
                    id=run_uuid,
                    ts=start_time.timestamp(),
                    temperature=bme_data[0],
                    humidity=bme_data[1],
                    pressure=bme_data[2],
                )
                # Send to weather-server
                r = requests.post("http://127.0.0.1:8000/weather/latest", json=payload)
            except:
                logger.info("Error saving data from BME Sensor.")

            try:
                print(f"Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}...")
                sensor_data = {
                    "temperature": bme_data[0],
                    "humidity": bme_data[1],
                    "pressure": bme_data[2],
                }
                payload = json.dumps(sensor_data)
                state_topic = f"homeassistant/sensor/{DEVICE_ID}/state"
                result = mqtt_client.publish(state_topic, payload, qos=1)
                result.wait_for_publish()
            except:
                logger.info("Publishing to MQTT failed")
        except:
            logger.info("Error fetching data from BME Sensor.")

        # fetch and save air quality data
        try:
            pms_data = sensors.pms_sensor.read_all()
            try:
                payload = {
                    "id": run_uuid,
                    "ts": start_time.timestamp(),
                    "pm1": pms_data.pm_ug_per_m3(1.0),
                    "pm2_5": pms_data.pm_ug_per_m3(2.5),
                    "pm10": pms_data.pm_ug_per_m3(10),
                }
                # Write to local database
                write_latest_air(
                    id=run_uuid,
                    ts=start_time.timestamp(),
                    pm1=pms_data.pm_ug_per_m3(1.0),
                    pm2_5=pms_data.pm_ug_per_m3(2.5),
                    pm10=pms_data.pm_ug_per_m3(10),
                )
                # Send to weather-server
                r = requests.post("http://127.0.0.1:8000/air/latest", json=payload)
            except:
                logger.info("Error saving data from PMS Sensor.")
        except:
            logger.info("Error fetching data from PMS Sensor.")

        logger.info("Data pull complete.")

        # calculate how long to wait
        finish_time = datetime.datetime.now(tz=ZoneInfo("UTC"))
        calc_time = (finish_time - start_time).total_seconds()
        time.sleep(max(0, 60 - calc_time))

    return None


def main():
    logging.basicConfig(
        filename="weather-logger.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Initialize database tables
    print("Triggering table initiation for weather-logger database")
    initiate_tables(LOGGER_DB)

    # Create an MQTT client instance
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CLIENT_ID)

    # Set up callbacks
    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish

    # wait for the discovery message to be created
    publish_discovery_messages(mqtt_client)
    time.sleep(2)

    async def readingsWorker():
        while True:
            log_readings(mqtt_client)

    #    async def secondWorker():
    #        while True:
    #            await asyncio.sleep(1)
    #            print("Second Worker Executed")

    loop = asyncio.get_event_loop()
    print("Starting Server")
    logger.info("Starting Server")
    try:
        asyncio.ensure_future(readingsWorker())
        #        asyncio.ensure_future(secondWorker())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping Server")
        mqtt_client.publish(
            f"homeassistant/sensor/{DEVICE_ID}/availability",
            "offline",
            qos=1,
            retain=True,
        )
        mqtt_client.disconnect()
        logger.info("Stopping Server")
        loop.close()


if __name__ == "__main__":
    main()
