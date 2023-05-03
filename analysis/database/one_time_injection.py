import datetime
import time
import logging
from analysis.sql_utils.db_handler import DBHandler, TableSpecs


class Injector:
    # def __init__(self, **kwargs):
    @staticmethod
    def get_insert_values(table, data, skip_first=True):
        # Gather expected table columns
        table_cols = list(TableSpecs.table_column_specs[table].items())[skip_first:]

        # Individual table modifications
        if table == 'drive_day':
            data['date'] = datetime.date.today().isoformat()
        elif table == 'event':
            data['creation_time'] = int(time.time() * 1000)
            table_cols = list(filter(lambda col: col[0] != 'event_index', table_cols))

        # Find columns missing from Flask app injection
        missing_cols = [col for col, _ in table_cols if col not in data]
        if missing_cols:
            logging.warning(f'\t\tFollowing columns were missing from transmitted data: {", ".join(missing_cols)}')

        # Separate NaNs and log
        nan_vals = [val == 0 or bool(val) for _, val in data.items()]
        nans = {key: val for (key, val), nan in zip(data.items(), nan_vals) if not nan}
        data = {key: val for (key, val), nan in zip(data.items(), nan_vals) if nan}
        if nans:
            logging.warning(f'\t\tFollowing columns had NaN data: {str(nans).replace(": ", " = ")[1:-1]}')

        return ', '.join(data.keys()), list(data.values())

    @classmethod
    def insert(cls, table, user='analysis', data=None):
        if data is None:
            raise ValueError('No data in payload.')

        cols, vals = cls.get_insert_values(table, dict(data))

        with DBHandler().connect(user=user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(f'''INSERT INTO {table} ({cols})
                                VALUES (%s{', %s' * (len(vals) - 1)}) 
                                RETURNING {list(TableSpecs.table_column_specs[table].keys())[0]}''', vals)
                return cur.fetchone()[0]

    @classmethod
    def set_event_time(cls, event_id, user='analysis', start=True):
        now = int(time.time() * 1000)
        with DBHandler().connect(user=user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(f'''UPDATE event SET {'start' if start else 'stop'}_time = {now}
                                WHERE event_id = {event_id}
                                RETURNING {'start' if start else 'stop'}_time''')
                return cur.fetchone()[0] == now



if __name__ == '__main__':
    Injector.get_insert_values('drive_day')