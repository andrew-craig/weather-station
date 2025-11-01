from flask import Flask, render_template, jsonify, request
import sqlite3
import os
import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)
app = Flask(__name__)

BIRD_DB = '/home/operator/bird-listener/db/bird-observations.db'
WEATHER_DB = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db/weather-server.db')

def initiate_tables(db_path):
    tables = [{'name':'thp_readings', 'columns':'id text, ts integer, temperature real, humidity real, pressure real'},
              {'name':'air_quality_readings', 'columns':'id text, ts integer, pm1 real, pm2_5 real, pm10 real'}]
    logger.info(f'Initiating {len(tables)} tables.')
    print('Initiating tables')
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    for table in tables:
        print('Initiating a table')
        print(table.get('name'))
        print(table.get('columns'))
        cursor.execute("""CREATE TABLE IF NOT EXISTS {table_name} ({columns})""".format(table_name=table.get('name'), columns=table.get('columns')))
    connection.commit()
    connection.close()
    print('Completed table initiation')
    logger.info(f'Completed table initiation.')
    return True

def query_weather(query):
    connection = sqlite3.connect(WEATHER_DB)
    cursor = connection.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    connection.close()
    return data

def write_weather(query):
    connection = sqlite3.connect(WEATHER_DB)
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    connection.close()
    return True

def query_latest_air():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 300
    data = query_weather("select pm1, pm2_5, pm10, ts from air_quality_readings where ts > {min_ts} order by ts desc limit 1".format(min_ts=min_ts))
    if not data:
        raise ValueError('No recent readings')
    else:
        r = {"pm1": data[0][0], "pm2_5": data[0][1], "pm10": data[0][2], "reading_time": data[0][3]}
        return r
    
def write_latest_air(id: str, ts: float, pm1: float, pm2_5: float, pm10: float):
    query = f"""INSERT INTO air_quality_readings VALUES('{id}', {ts}, {pm1}, {pm2_5}, {pm10})"""
    write_weather(query)
    return True

def query_latest_weather():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 300
    data = query_weather("select temperature, humidity, pressure, ts from thp_readings where ts > {min_ts} order by ts desc limit 1".format(min_ts=min_ts))
    if not data:
        raise ValueError('No recent readings')
    else:
        r = {"temp": data[0][0],"humidity": data[0][1], "pressure": data[0][2], "reading_time": data[0][3]}
        return r

def write_latest_weather(id: str, ts: float, temperature: float, humidity: float, pressure: float):
    query = f"""INSERT INTO thp_readings VALUES('{id}', {ts}, {temperature}, {humidity}, {pressure})"""
    print(query)
    write_weather(query)
    return True

def query_recent_air():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 300
    data = query_weather("select avg(pm1), avg(pm2_5), avg(pm10), count(id), max(ts) from air_quality_readings where ts > {min_ts} ".format(min_ts=min_ts))
    if data[0][3] == 0:
        raise ValueError('No recent readings')
    else:
        r = {"pm1": data[0][0], "pm2_5": data[0][1], "pm10": data[0][2], "num_readings": data[0][3], "latest_reading": data[0][4]}
        return r
    
def query_recent_weather():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 300
    data = query_weather("select avg(temperature), avg(humidity), avg(pressure), count(id), max(ts) from thp_readings where ts > {min_ts} ".format(min_ts=min_ts))
    if data[0][3] == 0:
        raise ValueError('No recent readings')
    else:
        r = {"temp": data[0][0],"humidity": data[0][1], "pressure": data[0][2], "num_readings": data[0][3], "latest_reading": data[0][4]}
        return r

def query_birds(query):
    connection = sqlite3.connect(BIRD_DB)
    cursor = connection.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    connection.close()
    return data

def get_recent_birds():
    min_ts = datetime.datetime.now(tz=ZoneInfo('UTC')).timestamp() - 60
    data = query_birds("select common_name, sum(confidence) from observations where ts > {min_ts} and confidence > 0.1 group by 1 order by 2 desc".format(min_ts=min_ts))
    l = []
    for d in data:
        l.append(d[0])
    return l

def safe_get_from_list(list: list, index: int):
    try:
        return list[index]
    except IndexError:
        return None


@app.route('/')
def index():
    # fetch the data
    try:
        weather_data = query_recent_weather()
    except:
        weather_data = {}
    try:
        air_data = query_recent_air()
    except:
        pass
    bird_list = get_recent_birds()
    # generate the site
    return render_template('web-app.html', 
                           temp="{:.0f}".format(weather_data.get('temp')) or 'n/a', 
                           humidity="{:.0f}".format(weather_data.get('humidity')) or 'n/a', 
                           pressure="{:.0f}".format(weather_data.get('pressure')) or 'n/a', 
                           pm1="{:.0f}".format(air_data.get('pm1')) or 'n/a', 
                           pm25="{:.0f}".format(air_data.get('pm2_5')) or 'n/a', 
                           pm10="{:.0f}".format(air_data.get('pm10')) or 'n/a',
                           bird_list=bird_list
                        )

@app.route('/weather/latest', methods=['GET','POST'])
def latest_weather():
    logger.info(f'Received {request.method} request to /weather/latest.')
    if request.method == 'POST':
        try:
            r = request.get_json()
            write_latest_weather(id=r.get('id'), ts=r.get('ts'), temperature=r.get('temperature'), humidity=r.get('humidity'), pressure=r.get('pressure'))
            return jsonify({'success':True}), 200, {'ContentType':'application/json'} 
        except:
            logger.info(f'Experienced an error processing POST request to /weather/latest')
            return jsonify({ 'error': 'Request data issue' }), 400
    else:
        try: 
            return jsonify(query_latest_weather())
        except ValueError:
            logger.info(f'Experienced an error processing GET request to /weather/latest')
            return jsonify({ 'error': 'No recent readings' }), 500


@app.route('/weather/recent', methods=['GET'])
def read_recent_weather():
    try: 
        return jsonify(query_recent_weather())
    except ValueError:
        return jsonify({ 'error': 'No recent readings' }), 500

@app.route('/air/latest', methods=['GET','POST'])
def latest_air():
    if request.method == 'POST':
        try:
            r = request.get_json()
            write_latest_air(id=r.get('id'), ts=r.get('ts'), pm1=r.get('pm1'), pm2_5=r.get('pm2_5'), pm10=r.get('pm10'))
            return jsonify({'success':True}), 200, {'ContentType':'application/json'} 
        except:
            return jsonify({ 'error': 'Request data issue' }), 400
    else:
        try: 
            return jsonify(query_latest_air())
        except ValueError:
            return jsonify({ 'error': 'No recent readings' }), 500


@app.route('/air/recent', methods=['GET'])
def read_recent_air():
    try: 
        return jsonify(query_recent_air())
    except ValueError:
        return jsonify({ 'error': 'No recent readings' }), 500

@app.route('/birds/recent_ha', methods=['GET'])
def read_recent_birds_ha():
    try: 
        l = get_recent_birds()
        s = ', '.join(l)
        st = (s[:252] + '...') if len(s) > 255 else s
        return jsonify({'birds': st})
    except ValueError:
        return jsonify({ 'error': 'No recent readings' }), 500

@app.route('/birds/recent', methods=['GET'])
def read_recent_birds():
    try: 
        l = get_recent_birds()
        return jsonify({'birds': l})
    except ValueError:
        return jsonify({ 'error': 'No recent readings' }), 500

if __name__ == '__main__':
    logging.basicConfig(filename='weather-server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print('Triggering table initiation')
    initiate_tables(WEATHER_DB)
    app.run(debug=True, host='0.0.0.0',  port=5005)
