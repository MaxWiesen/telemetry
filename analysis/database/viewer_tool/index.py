<<<<<<< HEAD
import json
import sys
import time
from datetime import datetime
from pathlib import Path
import requests
from flask_cors import CORS
=======
import logging
import json
import sys
from pathlib import Path
>>>>>>> origin/main
sys.path.append(str(Path(__file__).parents[3]))

from flask import Flask, render_template, url_for, request, redirect
from analysis.sql_utils.db_handler import DBHandler
from stack.ingest.mqtt_handler import mosquitto_connect

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    day_id = DBHandler.insert(table='drive_day', target='PROD', user='electric', data=request.args, returning='day_id')
    return redirect(url_for('.new_event', day_id=day_id, method='new'))


@app.route('/new_event/', methods=['GET'])
def new_event():
    return render_template('input_screen.html', day_id=request.form.get('day_id', request.args['day_id']))


@app.route('/create_event/', methods=['POST'])
def create_event():
<<<<<<< HEAD
    day_id, event_id = DBHandler.insert(table='event', user='electric', data=request.form, returning=['day_id', 'event_id'])
    client = mosquitto_connect()
    client.publish('flask', json.dumps({'event_id': event_id}, indent=4))
    return render_template('event_tracker.html', event_id=event_id, now = "00:00.000", time_started = False)
=======
    day_id, event_id = DBHandler.insert(table='event', target='PROD', user='electric', data=request.form, returning=['day_id', 'event_id'])
    client = mosquitto_connect('flask_sender')
    client.publish('config/flask', json.dumps({'event_id': event_id}, indent=4))
    return render_template('event_tracker.html', event_id=event_id)
>>>>>>> origin/main


@app.route('/set_event_time/', methods=['GET', 'POST'])
def set_event_time():
<<<<<<< HEAD
    return render_template('event_tracker.html')
=======
    event_id = int(request.form['event_id'])
    day_id = DBHandler.set_event_time(event_id, 'PROD', 'electric', 'start' in request.form, 'day_id')
    if 'start' not in request.form:
        client = mosquitto_connect('flask_sender')
        client.publish('config/flask', json.dumps({'end_event': True}, indent=4))
    return render_template('event_tracker.html', event_id=event_id)
>>>>>>> origin/main

@app.route('/turn_data', methods=['GET','POST'])
def turn_data():
    data = request.data
    print(data)
    return render_template('event_tracker.html')

@app.route('/accel_data', methods=['GET','POST'])
def accel_data():
    data = request.data
    print(data)
    return render_template('event_tracker.html')

if __name__ == '__main__':
<<<<<<< HEAD
    app.run(host='0.0.0.0', port=5001)
=======
    app.run(host='0.0.0.0', debug=True)
>>>>>>> origin/main
