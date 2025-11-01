# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi-based home weather station with two services:
- **weather-logger.py**: Reads sensor data every minute, stores locally, and publishes to MQTT (HomeAssistant integration)
- **weather-server.py**: Flask web server providing a web interface and REST API for weather data

Hardware sensors:
- BME280: Temperature, humidity, and pressure (I2C)
- PMS5003: Particulate matter PM1, PM2.5, PM10 (Serial)

## Development Commands

### Running Services

Test the logger (runs once per minute):
```bash
python weather-logger.py
```

Test the web server (development mode on port 5005):
```bash
python weather-server.py
```

Run the server with gunicorn (production):
```bash
gunicorn --workers 2 -m 007 weather-server:app
```

### Database Migration

If migrating from old unified database to separate databases:
```bash
python db_migration.py
```

## Architecture

### Two-Database Design

The system uses **separate SQLite databases** for the logger and server:
- `db/weather-logger.db`: Used by weather-logger.py for local persistence
- `db/weather-server.db`: Used by weather-server.py to serve data via API and web

Data flows from logger → server via HTTP POST to `http://127.0.0.1:5005/weather/latest` and `/air/latest`.

### Sensor Integration

Sensors are abstracted in the `sensors/` directory:
- `sensors/bme_sensor.py`: BME280 on I2C (port 1, address 0x76)
- `sensors/pms_sensor.py`: PMS5003 on serial `/dev/serial0`

Both expose a `read_all()` function returning sensor data.

### MQTT and HomeAssistant

weather-logger.py publishes to MQTT broker at `hub.local:1883`:
- Publishes HomeAssistant MQTT discovery messages on startup
- Sends state updates to `homeassistant/sensor/{DEVICE_ID}/state`
- Device availability tracked at `homeassistant/sensor/{DEVICE_ID}/availability`

MQTT client uses `paho-mqtt` with QoS 1 and retain flags for discovery.

### Database Schema

Both databases share identical tables:

**thp_readings**: `id text, ts integer, temperature real, humidity real, pressure real`
**air_quality_readings**: `id text, ts integer, pm1 real, pm2_5 real, pm10 real`

IDs are UUID7 strings. Timestamps are Unix epoch (seconds since 1970) in UTC.

### Flask API Endpoints

- `GET /`: Web interface showing current readings
- `GET/POST /weather/latest`: Most recent weather reading (last 5 minutes)
- `GET /weather/recent`: Average weather over last 5 minutes
- `GET/POST /air/latest`: Most recent air quality reading
- `GET /air/recent`: Average air quality over last 5 minutes
- `GET /birds/recent`: Returns bird observations (external integration with bird-listener)
- `GET /birds/recent_ha`: HomeAssistant-compatible bird list (max 255 chars)

POST endpoints expect JSON with: `id, ts, temperature, humidity, pressure` or `id, ts, pm1, pm2_5, pm10`.

### External Dependencies

weather-server.py integrates with a separate bird-listener service:
- Database: `/home/operator/bird-listener/db/bird-observations.db`
- Displays recent bird observations on web interface

## Key Implementation Details

### Error Handling

Both services use try/except blocks extensively to handle sensor failures gracefully. Logger continues running even if one sensor fails.

### Timing

weather-logger.py uses adaptive sleep to maintain 60-second intervals:
```python
calc_time = (finish_time - start_time).total_seconds()
time.sleep(max(0, 60 - calc_time))
```

### Logging

Both services log to files:
- `weather-logger.log`
- `weather-server.log`

Format: `%(asctime)s - %(levelname)s - %(message)s`

### Production Deployment

Services run as systemd units on Raspberry Pi:
- `weather-logger.service`: Runs logger with auto-restart
- `weather-server.service`: Runs gunicorn with 2 workers
- nginx reverse proxy on port 80 forwards to gunicorn on port 8000
