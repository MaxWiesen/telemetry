import json
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[3]))
from flask import Flask, render_template, url_for, request, redirect

from analysis.sql_utils.db_handler import DBHandler, DBTarget
from stack.ingest.mqtt_handler import MQTTHandler

app = Flask(__name__)

config = {}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    day_id = DBHandler.insert(table='drive_day', target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', data=request.args, returning='day_id')
    return redirect(url_for('.new_event', day_id=day_id, method='new'))


@app.route('/new_event/', methods=['GET'])
def new_event():
    return render_template('input_screen.html', day_id=request.form.get('day_id', request.args['day_id']))


@app.route('/create_event/', methods=['POST'])
def create_event():
    inputs = request.form.to_dict()
    inputs['status'] = 2
    try:
        last_packet = DBHandler.simple_select('SELECT packet_end FROM event WHERE status = 0 ORDER BY event_id DESC LIMIT 1')[0][0]
    except IndexError:
        last_packet = 0
    inputs['packet_start'] = last_packet + 1
    day_id, event_id = DBHandler.insert(table='event', target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', data=inputs, returning=['day_id', 'event_id'])
    with MQTTHandler('flask_app') as mqtt:
        mqtt.publish('/config/flask', json.dumps({'event_id': event_id}, indent=4))
    return render_template('event_tracker.html', host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET', DBTarget.LOCAL)), event_id=event_id)


@app.route('/set_event_time/', methods=['POST'])
def set_event_time():
    if request.json['status'] == 0:
        try:
            request.json['packet_end'] = DBHandler.simple_select('SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1')[0]
        except IndexError:
            request.json['packet_end'] = 1
        with MQTTHandler('flask_app') as mqtt:
            mqtt.publish('/config/flask', 'end_event')
    DBHandler.set_event_status(**request.json, target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', returning='day_id')
    return render_template('event_tracker.html', host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET', DBTarget.LOCAL)), event_id=request.json['event_id'])


@app.route('/tune_data', methods=['GET', 'POST'])
def tune_data():
    data = request.data
    json_object = json.loads(data)
    print(json_object)
    return render_template('texas_tune.html')


@app.route('/turn_data', methods=['GET', 'POST'])
def turn_data():
    data = request.data
    json_object = json.loads(data)
    print(json_object)
    return render_template('event_tracker.html', host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET', DBTarget.LOCAL)))


@app.route('/accel_data', methods=['GET', 'POST'])
def accel_data():
    data = request.data
    json_object = json.loads(data)
    print(json_object)
    return render_template('event_tracker.html', host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET', DBTarget.LOCAL)))


@app.route('/texas_tune/', methods=['GET', 'POST'])
def vcu_parameters():
    if request.method == 'POST':
        print(request)
    elif request.method == 'GET':
        return render_template('texas_tune.html')


@app.route('/gates/', methods=['POST'])
def create_gates():
    pass

@app.route('/new_lap/', methods=['POST'])
def add_new_lap():
    if "laps" not in config:
        config["laps"] = []
    data = request.form
    if "time" in data:
        config["laps"].append(data["time"])
        notify_listeners()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 
        
def notify_listeners():
    print(config)
    with MQTTHandler('flask_app') as mqtt:
        mqtt.publish('event_sync', json.dumps(config, indent=4))


if __name__ == '__main__':
    if os.getenv('IN_DOCKER'):
        app.run(host='0.0.0.0', ssl_context=('./ssl/fullchain.pem', './ssl/privkey.pem'))
    else:
        app.run(host='0.0.0.0', debug=True)