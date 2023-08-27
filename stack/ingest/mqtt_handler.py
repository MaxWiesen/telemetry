import os
import logging
import json
from paho.mqtt import client as mqtt_client
if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, get_table_column_specs    # Cheesed import statement using bind mount
else:
    from analysis.sql_utils.db_handler import DBHandler, get_table_column_specs


def mosquitto_connect():
    client = mqtt_client.Client('python_client')
    client.on_connect = lambda clients, userdata, flags, rc: logging.error(f'Failed to connect to Mosquitto Broker, return code {rc}\n') if rc \
        else logging.info('Python Client connected to Moquitto Broker')
    client.connect('mosquitto' if os.getenv('IN_DOCKER') else 'localhost')
    return client


def main():
    client = mosquitto_connect()

    def on_message(clients, userdata, msg):
        table = msg.topic.rsplit('/', 1)[-1]
        payload = json.loads(msg.payload.decode())
        logging.info(table in get_table_column_specs())
        logging.info(table)
        logging.info(get_table_column_specs())
        if table == 'flask':
            if (event_id := payload.get('event_id')):
                os.environ['EVENT_ID'] = event_id
        # if table == 'start' or table == 'stop':
        #     DBHandler.set_event_time()
        elif table in get_table_column_specs():
            logging.info(f'Data received for {table}. Inserting to Database now...')
            DBHandler.insert(table, user='electric', data=payload)
        else:
            logging.error(f'Table requested in MQTT topic does not exist in Database.')

    client.subscribe('#')
    client.on_message = on_message
    client.loop_forever()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()