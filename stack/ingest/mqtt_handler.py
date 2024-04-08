import datetime
import os
import logging
import json
import pickle
import base64
import numpy as np
from paho.mqtt import client as mqtt_client

if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, get_table_column_specs    # Cheesed import statement using bind mount
else:
    from analysis.sql_utils.db_handler import DBHandler, get_table_column_specs


class MQTTHandler:

    def __init__(self, name='python_client'):
        '''
        :param name:    str determining name of client to self-report to MQTT broker
        '''
        self.client = mqtt_client.Client(name)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    @staticmethod
    def on_connect(client: mqtt_client.Client, userdata, flags: dict, rc: int):
        if rc:
            logging.error(f'Failed to connect to Mosquitto Broker, return code {rc}\n')
        else:
            logging.info(f'\t\t{client} connected to Mosquitto Broker')

    @staticmethod
    def on_disconnect(client: mqtt_client.Client, userdata, rc: int):
        if rc != 0:
            print(f'Unexpected MQTT disconnection. Return code: {rc}')

    def on_message(self, client: mqtt_client.Client, userdata, msg):
        logging.info(f'Received message at topic {msg.topic}: {msg.payload}')
        if msg.topic == '/config/flask':
            self.flask_handler(json.loads(msg.payload.decode()))
        elif msg.topic == '/config/car':
            os.environ['RTC_START'] = str(datetime.datetime.strptime(msg.payload.decode(), "%Y-%m-%dT%H:%M:%S.%f").timestamp() * 1000)
        elif (freq := msg.topic.rsplit('/')[-1]) in ['h', 'l']:
            self.data_ingester(msg.payload, freq)
        else:
            logging.warning(f'No corresponding topic found for {msg.topic}')

    def connect(self, ip=None):
        '''
        Connect to the MQTT broker.

        :param ip:      str indicating IP of MQTT broker

        :return:        mqtt_client.Client object
        '''
        self.client.connect(ip if ip else 'mosquitto' if os.getenv('IN_DOCKER') else 'localhost')
        return self.client

    def disconnect(self):
        self.client.disconnect()

    def subscribe(self, topic: str = '#'):
        self.client.subscribe(topic)
        self.client.loop_forever()

    def publish(self, *args, **kwargs):
        self.client.publish(*args, **kwargs)

    def flask_handler(self, payload):
        if event_id := payload.get('event_id'):
            logging.info(f'Now logging data for event: {event_id}...')
            os.environ['EVENT_ID'] = str(event_id)

        elif payload.get('end_event'):
            logging.info(f'Ending logging for event {os.environ["EVENT_ID"]}...')
            del os.environ['EVENT_ID'], os.environ['RTC_START']

    def data_ingester(self, payload, high_freq: bool):
        if not os.getenv('EVENT_ID'):
            logging.error(f'Attempt made to send data without an event_id cached.')
            return
        
        logging.info(f'Data received. Inserting to Database now...')
        if not isinstance(payload, bytes):
            try:
                payload = pickle.loads(payload)
                logging.info('Pickle Payload received, likely coming from debug source...')
            except pickle.UnpicklingError:
                payload = json.loads(payload.decode().replace("'", '"'))
        db_desc = get_table_column_specs(force=True)
        data_dict = self.base64_decode(payload, True)
        data_dict = self.preprocess_payload(data_dict, high_freq)
        for table in ['dynamics', 'controls', 'pack', 'diagnostics', 'thermal']:
            DBHandler.insert(table, target='PROD', user='electric',
                             data={col: data_dict[col] for col in db_desc[table] if col in data_dict})

    @staticmethod
    def base64_decode(payload: str, high_freq: bool) -> dict:
        bytes_data = bytearray(base64.b64decode(payload))

        with open(f'car_configs/version{bytes_data[0]:02}.json', 'r') as file:
            config = json.load(file)['high' if high_freq else 'low']

        output = {}
        scalar_or_list = lambda val, scalar: val.tolist()[0] if scalar else val.tolist()
        for col, desc in config.items():
            if col in ['vcu_flags', 'current_errors', 'latching_faults']:
                output[col] = bin(int.from_bytes(bytes_data[desc['indices'][0]:desc['indices'][1]],
                                                 byteorder='big'))[2:]
            else:
                output[col] = scalar_or_list(np.frombuffer(bytes_data[desc['indices'][0]:desc['indices'][1]],
                                                           count=np.prod(desc.get('shape', -1)), dtype=desc['type']
                                                           ) * desc.get('multiplier', 1), not bool(desc.get('shape')))
        return output

    @staticmethod
    def preprocess_payload(payload: dict, high_freq=True):
        try:
            payload['time'] = int(float(os.environ['RTC_START']) + payload['since_rtc'])
            del payload['since_rtc']
        except KeyError:
            raise KeyError('RTC Start was not set.')
        # payload['event_id'] = os.environ['EVENT_ID']
        payload['event_id'] = 1
        if high_freq:
            payload['gps'] = tuple(val / 60 for val in payload['gps'])
            payload['vcu_flags_json'] = {
                'inverter_on': bool(int(payload['vcu_flags'][0])),
                'r2d_buzzer_on': bool(int(payload['vcu_flags'][1])),
                'brake_light_on': bool(int(payload['vcu_flags'][2])),
                'drs_on': bool(int(payload['vcu_flags'][3])),
                'apps_fault': bool(int(payload['vcu_flags'][4])),
                'bse_fault': bool(int(payload['vcu_flags'][5])),
                'stompp_fault': bool(int(payload['vcu_flags'][6])),
                'steering_fault': bool(int(payload['vcu_flags'][7]))
            }

            # IMU Acceleration
            payload['body1_accel'] = payload['imu_accel'][:3]
            payload['body2_accel'] = payload['imu_accel'][3:6]
            payload['body3_accel'] = payload['imu_accel'][6:9]
            payload['flw_accel'] = payload['imu_accel'][9:12]
            payload['frw_accel'] = payload['imu_accel'][12:15]
            payload['blw_accel'] = payload['imu_accel'][15:18]
            payload['brw_accel'] = payload['imu_accel'][18:21]
            del payload['imu_accel']

            # IMU Gyro
            payload['body1_gyro'] = payload['imu_gyro'][:3]
            payload['body2_gyro'] = payload['imu_gyro'][3:6]
            payload['body3_gyro'] = payload['imu_gyro'][6:9]
            del payload['imu_gyro']

            # Wheel Speed
            payload['flw_speed'] = payload['wheel_speed'][:3]
            payload['frw_speed'] = payload['wheel_speed'][3:6]
            payload['blw_speed'] = payload['wheel_speed'][6:9]
            payload['brw_speed'] = payload['wheel_speed'][9:12]
            del payload['wheel_speed']


        return payload

    # TODO: Implement with enter for auto disconnect
    # def __enter__(self):
    #     self.client.connect()
    #     return self.client
    #
    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     self.client.disconnect()


def main():
    '''
    This is the runner script for the subscribe-side MQTT script which uploads data to the database
    '''
    # mqtt = MQTTHandler('paho_tester')
    # mqtt.connect('ec2-52-14-184-219.us-east-2.compute.amazonaws.com')
    # mqtt.publish('config/flask', json.dumps({'event_id': 'idk'}, indent=4))

    os.environ['RTC_START'] = str((datetime.datetime.now().timestamp() - 3600 * 3) * 1000)
    mqtt = MQTTHandler('ingest')
    # data = mqtt.base64_decode(b'AUQWAAAAAL4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABdAWYBAgBfAToBQgFxAEkxFgGMSYH8EgDZagAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', True)
    data = mqtt.base64_decode(b'AQAAAAAAqqNAAAAAADCNCkEAAAAAANbZQAAAAABQbBFBAAAAAMAe50AAAAAAgFnSQAAAAADc5UVBAAAAANqkQkEAAAAA3vRIQQAAAIAk8X5BAAAAAIhfXUEAAAAAwZRtQQAAAAC2AUFBAAAAABTeMkEAAAAAWJ8sQQAAAAAE9jRBAAAAAMjgNUEAAAAAAIBJQAAAAKCGTa1BAAAAAADAWUAAAACA0ft7QQAAAADz62tBAAAAACu/akEAAAAAWR1hQQAAAAAcBmpBAAAAAFBFdUEAAAAARgtYQQAAAIBQ/KRBAAAAQFwhn0EAAAAASAVCQQAAAACmfUNBAAAAAG5YYUEAAACA34JzQQAAAADsAVxBAAAAAKj1cUEAAAAAvTBiQQAAAAB3iWNBAAAAAPnwakEAAAAAT6dtQQAAAAD2O1lBAAAAAIABX0EAAAAARB1cQQAAAACIKlFBAAAAADtja0EAAACApO50QQAAAIDe0n5BAAAAgMB4eUEAAAAAy85qQQAAAADskGlBAAAAADSLaEEAAACAPsl9QQAAAABNE3NBAAAAAL4VQ0EAAAAAYilFQQAAAADYJTFBAAAAADgwRUEAAAAA9qpDQQAAAADoKCdBAAAAAEglNUEAAAAAsOsYQQAAAADAavtAAAAAAEAvDUEAAAAAYKcLQQAAAACIZRJBAAAAAAAMp0AAAAAAEPojQQAAAACgWTVBAAAAAEBA3UAAAAAAwKT9QA==', True)
    print(mqtt.preprocess_payload(data))
    # mqtt.connect('mosquitto')
    # mqtt.subscribe(topic='#')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
