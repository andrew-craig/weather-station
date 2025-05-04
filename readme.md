# Home Weather Station

A home weather station to run on a Raspberry Pi. There are two services, one to log readings once per minute, and one to serve the readings via web and API. I have two sensos:
* a BME280 for temperature, humidity and pressure
* a PMS5003 for particulate matter


## Installation
Install python-dev
> sudo apt install python3-dev

Navigate to the project directory
> cd ~/weather-station

Create a virtual environment
> python3 -m venv venv

Activate the virtual environment
> source venv/bin/activate

Install packages for the sensors
> pip install RPi.bme280 pms5003

Install the packages required for the logger
> pip install asyncio uuid7

Install packages for the webapp and API
> pip install flask gunicorn

Enable the serial port in `raspi-config`

If you want to use the Montserrat font, download `Montserrat-Regular.ttf` from [Google Fonts](https://fonts.google.com/specimen/Montserrat) and save it in the `static` folder.

## Testing
Test the logger
> python weather-logger.py
At this stage, as long as this runs without errors, it's ok.

Test the server
> python weather-server.py
This should spin up a development server that serves readings (as long as the most recent reading was in the last 5 minutes).

## Set up the services

Navigate to the systemd directory
> cd /etc/systemd/system

Create a new file `weather-logger.service`
> sudo nano weather-logger.service

Add the below to the file. Replace `operator` with your username.
    [Unit]
    Description=Service to fetch readings via API
    StartLimitIntervalSec=300
    StartLimitBurst=5
    
    [Service]
    ExecStart=/home/operator/weather-station/venv/bin/python /home/operator/weather-station/weather-logger.py   
    WorkingDirectory=/home/operator/weather-station   
    Restart=on-failure   
    RestartSec=5s   
    
    [Install]
    WantedBy=multi-user.target
Save and exit.

Enable the service
> sudo systemctl enable weather-logger

Start the service
> sudo systemctl start weather-logger

Create a new file `weather-server.service`
> sudo nano weather-server.service

Add the below to the file. Replace `operator` with your username.
    [Unit]
    Description=Service for weather station website and API
    StartLimitIntervalSec=300
    StartLimitBurst=5

    [Service]
    User=operator
    ExecStart=/home/operator/weather-station/venv/bin/gunicorn --workers 2 -m 007 weather-server:app
    WorkingDirectory=/home/operator/weather-station
    Environment="PATH=/home/operator/weather-station/venv/bin"
    Restart=on-failure
    RestartSec=5s

    [Install]
    WantedBy=multi-user.target

Enable the service
> sudo systemctl enable weather-server

Start the service
> sudo systemctl start weather-server


## Setup nginx as a reverse proxy
Install nginx
> sudo apt install nginx

Navigate to the `sites-available` nginx directory
> cd /etc/nginx/sites-available

Create a new file `weather-server`
> sudo nano weather-server

Add the following to the file
    server {
        listen 80;
        server_name outside.local;

        location / {
            include proxy_params;
            proxy_pass http://127.0.0.1:8000;
        }
    }
Save and exit.

Make this available
> sudo ln -s /etc/nginx/sites-available/weather-server /etc/nginx/sites-enabled/weather-server



