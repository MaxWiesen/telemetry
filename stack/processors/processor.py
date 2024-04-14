import os
import logging
from time import sleep

if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, get_table_column_specs    # Cheesed import statement using bind mount
else:
    from analysis.sql_utils.db_handler import DBHandler, get_table_column_specs


class DBProcessor:
    def __init__(self, db_handler: DBHandler):
        self.handler = db_handler

    def check_alive(self):
        logging.info(self.handler.simple_select('''SELECT event_id FROM event WHERE status = 1''', handler=self.handler))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    handler = DBHandler()
    processor = DBProcessor(handler)
    while True:
        processor.check_alive()
        sleep(5)