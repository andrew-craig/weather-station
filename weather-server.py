from flask import Flask, render_template, jsonify
import sqlite3
import os
import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

def query_readings(query):
    connection = sqlite3.connect(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db/weather-readings.db'))
    cursor = connection.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    connection.close()
    return data


def query_latest():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 300
    data = query_readings("select temperature, humidity, pressure, pm_1, pm_2_5, pm_10, ts from readings where ts > {min_ts} order by ts desc limit 1".format(min_ts=min_ts))
    if not data:
        raise ValueError('No recent readings')
    else:
        reading_time = datetime.datetime.fromtimestamp(data[0][6], tz=ZoneInfo('UTC')).isoformat()
        r = {"temp": data[0][0],"humidity": data[0][1], "pressure": data[0][2], "PM1": data[0][3], "PM2.5": data[0][4], "PM10": data[0][5], "Reading Time": data[0][6]}
        return r

def query_recent():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 300
    data = query_readings("select avg(temperature), avg(humidity), avg(pressure), avg(pm_1), avg(pm_2_5), avg(pm_10), count(id) from readings where ts > {min_ts} ".format(min_ts=min_ts))
    if data[0][6] == 0:
        raise ValueError('No recent readings')
    else:
        r = {"temp": data[0][0],"humidity": data[0][1], "pressure": data[0][2], "PM1": data[0][3], "PM2.5": data[0][4], "PM10": data[0][5], "Num Readings": data[0][6]}
        return r

@app.route('/')
def index():
    # fetch the data
    data = query_recent()
   
    # generate the site
    return render_template('web-app.html', 
                           temp="{:.0f}".format(data.get('temp')), 
                           humidity="{:.0f}".format(data.get('humidity')), 
                           pressure="{:.0f}".format(data.get('pressure')), 
                           pm1="{:.0f}".format(data.get('PM1')), 
                           pm25="{:.0f}".format(data.get('PM2.5')), 
                           pm10="{:.0f}".format(data.get('PM10')), 
                        )

@app.route('/readings/latest', methods=['GET'])
def read_latest():
    try: 
        return jsonify(query_latest())
    except ValueError:
        return jsonify({ 'error': 'No recent readings' }), 500


@app.route('/readings/recent', methods=['GET'])
def read_recent():
    try: 
        return jsonify(query_recent())
    except ValueError:
        return jsonify({ 'error': 'No recent readings' }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',  port=5005)