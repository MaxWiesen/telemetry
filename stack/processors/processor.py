import os
import logging
from time import sleep
import pandas as pd
import numpy as np

from stack.ingest.mqtt_handler import MQTTHandler

if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, get_table_column_specs    # Cheesed import statement using bind mount
else:
    from analysis.sql_utils.db_handler import DBHandler, get_table_column_specs


class DBProcessor:
    def __init__(self, db_handler: DBHandler=None):
        self.handler = db_handler if db_handler else DBHandler()

    def check_alive(self):
        logging.info(self.handler.simple_select('''SELECT event_id FROM event WHERE status = 1''', handler=self.handler))

    def sliding_window(self, f, query, window_size):
        self.handler.simple_select(query, handler=self.handler)


def main():
    with MQTTHandler() as mqtt:
        processor = DBProcessor()
        while True:
            processor.check_alive()
            sleep(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
