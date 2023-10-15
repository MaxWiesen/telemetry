import logging
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[3]))

from flask import Flask, render_template, url_for, request, redirect
from analysis.sql_utils.db_handler import DBHandler
from stack.ingest.mqtt_handler import mosquitto_connect

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    day_id = DBHandler.insert(table='drive_day', user='electric', data=request.args, returning='day_id')
    return redirect(url_for('.new_event', day_id=day_id, method='new'))


@app.route('/new_event/', methods=['GET'])
def new_event():
    return render_template('input_screen.html', day_id=request.form.get('day_id', request.args['day_id']))


@app.route('/create_event/', methods=['POST'])
def create_event():
    day_id, event_id = DBHandler.insert(table='event', user='electric', data=request.form, returning=['day_id', 'event_id'])
    client = mosquitto_connect()
    client.publish('flask', json.dumps({'event_id': event_id}, indent=4))
    return render_template('event_tracker.html', event_id=event_id)


@app.route('/set_event_time/', methods=['POST'])
def set_event_time():
    event_id = int(request.form['event_id'])
    day_id = DBHandler.set_event_time(event_id, 'electric', 'start' in request.form, 'day_id')
    if 'start' not in request.form:
        client = mosquitto_connect()
        client.publish('flask', json.dumps({'end_event': True}, indent=4))
    return render_template('event_tracker.html', event_id=event_id)


if __name__ == '__main__':
    app.run(host='0.0.0.0:5001', debug=True)
