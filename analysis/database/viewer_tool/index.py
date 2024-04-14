import json
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[3]))
from flask import Flask, render_template, url_for, request, redirect

from analysis.sql_utils.db_handler import DBHandler
from stack.ingest.mqtt_handler import MQTTHandler

app = Flask(__name__)

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
    inputs = request.form.to_dict()
    inputs['status'] = 2
    day_id, event_id = DBHandler.insert(table='event', target='PROD', user='electric', data=inputs, returning=['day_id', 'event_id'])
    mqtt = MQTTHandler('flask_app')
    mqtt.connect()
    mqtt.publish('config/flask', json.dumps({'event_id': event_id}, indent=4))
    mqtt.disconnect()
    return render_template('event_tracker.html', host_ip=os.getenv('HOST_IP', 'localhost'), event_id=event_id)


@app.route('/set_event_time/', methods=['POST'])
def set_event_time():
    DBHandler.set_event_status(**request.json, target='PROD', user='electric', returning='day_id')
    if request.json['status'] == 0:
        mqtt = MQTTHandler('flask_app')
        mqtt.connect()
        mqtt.publish('config/flask', 'end_event')
        mqtt.disconnect()
    return render_template('event_tracker.html', host_ip=os.getenv('HOST_IP', 'localhost'), event_id=request.json.get('event_id'))


@app.route('/tune_data', methods=['GET','POST'])
def tune_data():
    data = request.data
    json_object = json.loads(data)
    print(json_object)
    return render_template('texas_tune.html')


@app.route('/turn_data', methods=['GET','POST'])
def turn_data():
    data = request.data
    json_object = json.loads(data)
    print(json_object)
    return render_template('event_tracker.html', host_ip=os.getenv('HOST_IP', 'localhost'))


@app.route('/accel_data', methods=['GET','POST'])
def accel_data():
    data = request.data
    json_object = json.loads(data)
    print(json_object)
    return render_template('event_tracker.html', host_ip=os.getenv('HOST_IP', 'localhost'))


@app.route('/texas_tune/', methods=['GET', 'POST'])
def vcu_parameters():
    if request.method == 'POST':
        print(request)
    elif request.method == 'GET':
        return render_template('texas_tune.html')


@app.route('/gates/', methods=['POST'])
def create_gates():
    pass


if __name__ == '__main__':
    if os.getenv('IN_DOCKER'):
        app.run(host='0.0.0.0', ssl_context=('./ssl/fullchain.pem', './ssl/privkey.pem'))
    else:
        app.run(host='0.0.0.0', debug=True)