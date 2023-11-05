import os
import logging
import json
import pickle
from paho.mqtt import client as mqtt_client

if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, get_table_column_specs    # Cheesed import statement using bind mount
else:
    from analysis.sql_utils.db_handler import DBHandler, get_table_column_specs


def mosquitto_connect(name='python_client'):
    client = mqtt_client.Client(name)
    client.on_connect = lambda clients, userdata, flags, rc: logging.error(f'Failed to connect to Mosquitto Broker, return code {rc}\n') if rc \
        else logging.info(f'\t\t{name} connected to Mosquitto Broker')
    client.connect('mosquitto' if os.getenv('IN_DOCKER') else 'localhost')
    return client


def main():
    client = mosquitto_connect('mqtt_handler')

    def on_message(clients, userdata, msg):
        table = msg.topic.rsplit('/', 1)[-1]
        if table == 'flask':
            payload = json.loads(msg.payload.decode())
            if event_id := payload.get('event_id'):
                logging.info(f'Now logging data for event: {event_id}...')
                os.environ['EVENT_ID'] = str(event_id)
            elif payload.get('end_event'):
                logging.info(f'Now ending logging for event {os.environ["EVENT_ID"]}')
                del os.environ['EVENT_ID']
        elif table in get_table_column_specs():
            if not os.getenv('EVENT_ID'):
                logging.error(f'Attempt made to send data to {table} without an event_id cached.')
            payload = pickle.loads(msg.payload)
            logging.info(f'Data received for {table}. Inserting to Database now...')
            payload['event_id'] = os.getenv('EVENT_ID')
            DBHandler.insert(table, target='PROD', user='electric', data=payload)
        else:
            logging.error(f'Table {table} requested in MQTT topic does not exist in Database.')

    def on_disconnect(clients, userdata, rc):
        if rc != 0:
            print("Unexpected MQTT disconnection. Attempting to reconnect.")

    client.subscribe('#')
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.loop_forever()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
