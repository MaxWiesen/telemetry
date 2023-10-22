import json
import sys
import time
from datetime import datetime
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
    return render_template('event_tracker.html', event_id=event_id, now = "00:00.000", time_started = False)


@app.route('/set_event_time/', methods=['POST'])
def set_event_time():
    event_id = int(request.form['event_id'])
    day_id = DBHandler.set_event_time(event_id, 'electric', 'start' in request.form, 'day_id')
    if 'start' in request.form:
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
    if 'start' not in request.form:
        current_time = request.form['time']
        client = mosquitto_connect()
        client.publish('flask', json.dumps({'end_event': True}, indent=4))
    return render_template('event_tracker.html', time_started = ('start'  in request.form), now = current_time, event_id=event_id)

# @app.route('/start_turn/', methods=['POST'])
# def set_event_time():
#     event_id = int(request.form['event_id'])
#     day_id = DBHandler.set_event_time(event_id, 'electric', 'start' in request.form, 'day_id')
#     started = False
#     if 'start'  in request.form:
#         started = True
#     if 'start' not in request.form:
#         started = False
#         client = mosquitto_connect()
#         client.publish('flask', json.dumps({'end_event': True}, indent=4))
#     return render_template('event_tracker.html', time_started = started, event_id=event_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)