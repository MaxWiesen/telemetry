import datetime
import os
import logging
import json
import pickle
import base64
import time
import numpy as np
from paho.mqtt import client as mqtt_client

if os.getenv('IN_DOCKER'):
    from db_handler import get_table_column_specs, DBTarget, DBHandler    # Cheesed import statement using bind mount
else:
    from analysis.sql_utils.db_handler import get_table_column_specs, DBTarget, DBHandler


class MQTTTarget:
    LOCAL = 'localhost'
    PROD = 'telemetry.servebeer.com'


class MQTTHandler:

    def __init__(self, name='python_client', target=None):
        '''
        :param name:    str determining name of client to self-report to MQTT broker
        '''
        self.target = target
        self.client = mqtt_client.Client(name)
        self.client.username = name
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    @staticmethod
    def on_connect(client: mqtt_client.Client, userdata, flags: dict, rc: int):
        if rc:
            logging.error(f'Failed to connect to Mosquitto Broker, return code {rc}\n')
        else:
            logging.info(f'\t\t{client.username} connected to Mosquitto Broker')

    @staticmethod
    def on_disconnect(client: mqtt_client.Client, userdata, rc: int):
        if rc != 0:
            print(f'Unexpected MQTT disconnection. Return code: {rc}')

    def connect(self, ip=None):
        '''
        Connect to the MQTT broker.

        :param ip:      str indicating IP of MQTT broker

        :return:        mqtt_client.Client object
        '''
        self.client.connect(ip if ip else self.target if self.target else 'mosquitto' if os.getenv('IN_DOCKER') else 'localhost')
        return self.client

    def disconnect(self):
        self.client.disconnect()

    def __enter__(self):
        self.client.connect(self.target if self.target else 'mosquitto' if os.getenv('IN_DOCKER') else 'localhost')
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.disconnect()

    def subscribe(self, topic: str = '#'):
        self.client.subscribe(topic)
        self.client.loop_forever()

    def publish(self, *args, **kwargs):
        self.client.publish(*args, **kwargs)

    def on_message(self, client: mqtt_client.Client, userdata, msg):
        logging.info(f'Received message at topic {msg.topic}: {msg.payload}')
        if msg.topic == '/config/flask':
            self.__flask_handler(msg.payload.decode())
        elif msg.topic == '/config/car':
            os.environ['RTC_START'] = str(datetime.datetime.strptime(msg.payload.decode(), "%Y-%m-%dT%H:%M:%S.%f").timestamp() * 1000)
        elif (freq := msg.topic.rsplit('/')[-1]) in ['h', 'l']:
            self.__b64_ingest(msg.payload, freq)
        elif (topic_split := msg.topic.split('/'))[0] == 'data':
            self.__data_ingest(msg.payload, topic_split[-1])
        else:
            logging.warning(f'No corresponding topic found for {msg.topic}')

    def __flask_handler(self, payload):
        try:
            event_id = json.loads(payload)['event_id']
            logging.info(f'\tNow logging data for event: {event_id}...')
            os.environ['EVENT_ID'] = str(event_id)
        except json.JSONDecodeError:
            if payload == 'end_event':
                event_id = os.environ['EVENT_ID']
                del os.environ['EVENT_ID']
                try:
                    del os.environ['RTC_START']
                    logging.info(f'\tEnding logging for event {event_id}...')
                except KeyError:
                    logging.info(f'\tEnding logging for event {event_id} despite RTC_START never being set...')
            else:
                logging.error(f'\tUnexpected payload received: {payload}')

    def __data_ingest(self, payload, table):
        if not os.getenv('EVENT_ID'):
            logging.error(f'\tAttempt made to send data without an event_id cached.')

        logging.info(f'\tData received. Inserting to Database now...')
        try:
            data_dict = pickle.loads(payload)
            logging.info('\tPickle Payload received, likely coming from debug source...')
        except pickle.UnpicklingError:
            data_dict = json.loads(payload.decode().replace("'", '"'))
        DBHandler.insert(table, target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', data=data_dict)

    def __b64_ingest(self, payload, high_freq: bool):
        if not os.getenv('EVENT_ID'):
            logging.error(f'\tAttempt made to send data without an event_id cached.')

        logging.info(f'\tData received. Inserting to Database now...')
        data_dict = self.__base64_decode(payload, True)
        data_dict = self.preprocess_payload(data_dict, high_freq)
        db_desc = get_table_column_specs(force=True)
        for table in ['dynamics', 'controls', 'pack', 'diagnostics', 'thermal']:
            DBHandler.insert(table, target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric',
                             data={col: data_dict[col] for col in db_desc[table] if col in data_dict})

    def __base64_decode(self, payload: str, high_freq: bool) -> dict:
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
            payload['flw_speed'] = payload['wheel_speed'][0]
            payload['frw_speed'] = payload['wheel_speed'][1]
            payload['blw_speed'] = payload['wheel_speed'][2]
            payload['brw_speed'] = payload['wheel_speed'][3]
            del payload['wheel_speed']

        return payload


def main():
    '''
    This is the runner script for the subscribe-side MQTT script which uploads data to the database
    '''
    mqtt = MQTTHandler('ingest')
    mqtt.connect('mosquitto')
    mqtt.subscribe(topic='#')


if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'DEBUG'))
    if logging.root.level == logging.DEBUG:
        time.sleep(1)
        logging.debug('-' * 40 + '\n\n\t\tYOU ARE IN DEBUGGING MODE\n\n ' + '-' * 50)
        os.environ['RTC_START'] = "-99999"
        os.environ['EVENT_ID'] = "-99999"
    main()

    # mqtt = MQTTHandler('Test')
    # os.environ['RTC_START'] = '0'
    # os.environ['EVENT_ID'] = '0'
    # data = mqtt.base64_decode(b'AZMiAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAFNEAABUAAAA89gEAABmEC8oF/QHjAbkBlgFvAwQmgQG3wvz8PgBmif4Iev/K2gAAAAAAAMr+8/5LJ2HXT/1NAgAAAAAAAIX+rx3rGLcB1+MbGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKAAAAAAAAAA+I18TQMpCCb5QbRjBAAAAAAAAAAA=', True)
    # print(data)
    # print(MQTTHandler.preprocess_payload(data, True))
