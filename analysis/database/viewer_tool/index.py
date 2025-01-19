import json
import os
import sys
import time
from pathlib import Path
from tqdm import tqdm
sys.path.append(str(Path(__file__).parents[3]))
from flask import Flask, render_template, url_for, request, redirect

from analysis.sql_utils.db_handler import DBHandler, DBTarget
from stack.ingest.mqtt_handler import MQTTHandler, MQTTTarget

app = Flask(__name__)
config = {}
os.environ["event_details"] = ""
os.environ["eid"] = "-1"

def config_subscribe(client, userdata, msg):
    print("Callback hit")  # TODO DEBUG only

    if msg.topic == 'config/event_sync':
        #Convert msg to json object
        msg = json.loads(msg.payload.decode())
        #TODO safety, Ensure all fields present
        #Check for flags
        if "flag" in msg:
            print("Eval: " + str(msg["flag"] == "END"))
            #TODO tell database event is over

            # TODO REMOVE, STRICTLY DEBUG (Packet Generation)
            #for i in tqdm(range(1, 100)):
            #    DBHandler.insert('packet', target=DBTarget.LOCAL, user='electric', data={'packet_id': i, 'time': int(time.time())})

            last_pack = DBHandler.simple_select('SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1')[0][0]
            DBHandler.set_event_status(int(os.getenv("eid")), 0, packet_end=last_pack, user='electric')
        else:
            print("Key 'flag' is missing in the message payload.")
        #Store return
        os.environ["event_details"] = "" if ("flag" in msg and str(msg["flag"] == "END")) else json.dumps(msg)
        print("Index Event Details: " + os.getenv("event_details")) # TODO remove, debug only

def mqtt_client_loop(mqtt):
    # Start the MQTT client loop (this will run forever in the background)
    mqtt.client.loop_forever()

@app.route('/', methods=['GET'])
def index():
    #Check to see if an event already exists TODO db handler simple select event id, where status is 1
    print("EVENT DETAILS: " + os.getenv("event_details")) # TODO DEBUG only
    #if os.getenv("event_details"): original check
    try:
        os.environ["eid"] = str(DBHandler.simple_select('SELECT event_id FROM event WHERE status = 1 ORDER BY event_id DESC LIMIT 1')[0][0])
        print("Attempted Select Returned: " + os.getenv("eid")) #TODO REMOVE, debug only
    except Exception as e:
        print("Database event-running check failed with " + str(e))

    #TODO migrate from eid os env to request structure for all

    if os.getenv("eid") != "-1" or os.getenv("event_details"):
        return redirect(url_for('create_event'))
    #No existing event, normal path
    return render_template('index.html')

@app.route('/new_drive_day/', methods=['GET'])
def new_drive_day():
    day_id = DBHandler.insert(table='drive_day', target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', data=request.args, returning='day_id')
    return redirect(url_for('.new_event', day_id=day_id, method='new'))


@app.route('/new_event/', methods=['GET'])
def new_event():
    return render_template('input_screen.html', day_id=request.form.get('day_id', request.args['day_id']))


@app.route('/create_event/', methods=['POST', 'GET'])
def create_event():
    if request.method == 'POST':
        inputs = request.form.to_dict()
    else:
        return render_template('event_tracker.html',
                host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET', DBTarget.LOCAL)),
                event_id = 0, config_image = os.getenv("event_details")) #TODO RESOLVE ZERO
    inputs['status'] = 2
    try:
        last_packet = DBHandler.simple_select('SELECT packet_end FROM event WHERE status = 0 ORDER BY event_id DESC LIMIT 1')[0][0]
    except IndexError:
        last_packet = 0
    inputs['packet_start'] = last_packet + 1
    day_id, event_id = DBHandler.insert(table='event', target=os.getenv('SERVER_TARGET', DBTarget.LOCAL),
                                        user='electric', data=inputs, returning=['day_id', 'event_id'])
    with MQTTHandler('flask_app') as mqtt:
        mqtt.publish('config/flask', json.dumps({'event_id': event_id}, indent=4))
    return render_template('event_tracker.html', host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET',
                             DBTarget.LOCAL)), event_id=event_id, config_image = os.getenv("event_details"))


@app.route('/set_event_time/', methods=['POST'])
def set_event_time():
    if request.json['status'] == 0:
        try:
            request.json['packet_end'] = DBHandler.simple_select('SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1')[0][0]
        except IndexError:
            request.json['packet_end'] = 1
        with MQTTHandler('flask_app') as mqtt:
            mqtt.publish('config/flask', 'end_event')
    DBHandler.set_event_status(**request.json, target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', returning='day_id')
    return render_template('event_tracker.html', host_ip=DBTarget.resolve_target(os.getenv('SERVER_TARGET', DBTarget.LOCAL)), event_id=request.json['event_id'])

@app.route('/reset_config_image', methods=['POST', 'GET'])
def reset_config_image():
    os.environ['event_details'] = ""
    print("Config image reset. Event has ended.")
    return redirect(url_for('index'))
    #return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

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
    if 'laps' not in config:
        config['laps'] = []
    data = request.form
    if 'time' in data:
        config['laps'].append(data['time'])
        notify_listeners()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
def notify_listeners():
    print(config)
    with MQTTHandler('flask_app') as mqtt:
        mqtt.publish('event_sync', json.dumps(config, indent=4))


if __name__ == '__main__':

    with MQTTHandler('testerieses', target=MQTTTarget.LOCAL, on_message=config_subscribe) as mqtt:
        mqtt.client.subscribe('config/event_sync')
        mqtt.client.loop_start()

        if os.getenv('IN_DOCKER'):
            app.run(host='0.0.0.0', ssl_context=('./ssl/fullchain.pem', './ssl/privkey.pem'))
        else:
            app.run(host='0.0.0.0', debug=False)