import sqlite3
import os


def main():
    print("Initialising database connection")
    db_path = os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db'), 'weather-readings.db')
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    tph_q = """INSERT INTO thp_readings (id, ts, temperature, humidity, pressure)
    SELECT id, ts, temperature, humidity, pressure
    FROM readings"""

    air_q = """INSERT INTO air_quality_readings (id, ts, pm1, pm2_5, pm10)
    SELECT id, ts, pm1, pm2_5, pm10
    FROM readings"""

    print("Starting migration")
    cursor.execute(tph_q)
    connection.commit()
    connection.close()
    print("Migration complete")
    return True

if __name__ == '__main__':
    main()
