import pandas as pd
import psycopg
import pickle
import time
import logging
import datetime
import os


def get_table_column_specs(force=False, verbose=False):
    #TODO: 1) Find underlying data types of ARRAY; 2) Add point type compatibility
    desc_path = './DB_description.pkl' if os.getenv('IN_DOCKER') else os.getcwd().rsplit('analysis/', 1)[0] + 'analysis/sql_utils/DB_description.pkl'
    last_update, table_column_specs = pickle.load(open(desc_path, 'rb'))
    if not os.getenv('IN_DOCKER'):
        now = time.time()
        if force or now - last_update > 86_400 * 1:     # Days since last update
            with DBHandler().connect(user='electric') as cnx:
                with cnx.cursor() as cur:
                    cur.execute("""SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE 
                                   FROM INFORMATION_SCHEMA.COLUMNS 
                                   WHERE TABLE_SCHEMA = 'public'""")
                    data = pd.DataFrame(cur.fetchall(), columns=['table_name', 'column_name', 'data_type'])
                    data.data_type.replace({'smallint': int, 'integer': int, 'bigint': int, 'real': float, 'text': str,
                                            'boolean': bool, 'date': datetime.date, 'ARRAY': list}, inplace=True)
                    table_column_specs = {table: list(zip((table_data := data[data.table_name == table]).column_name,
                                                          table_data.data_type)) for table in data.table_name.unique()}
                pickle.dump((now, table_column_specs), open(desc_path, 'wb'))
                logging.info(f'\t\ttable_column_specs out of date and updated.')
                if verbose:     # Pretty print table column specs
                    [logging.info(f'\t\t{table}\n' + ''.join([f'\n{col:^20} {str(dtype):^30}' for col, dtype in col_data]) +
                                  '\n') for table, col_data in table_column_specs.items()]
    return table_column_specs


class DBHandler:
    DB_CONFIG = {
        'PROD': {
            'dbname': 'telemetry',
            'user': {
                'electric': '2fast2quick',
                'grafana': 'frontend',
                'analysis': 'north_dakota'
            },
            'host': 'db' if os.getenv('IN_DOCKER') else 'localhost',
            'port': 5432
        }
    }

    def connect(self, target='PROD', user='analysis'):
        if target not in self.DB_CONFIG:
            raise ValueError(f'Target server {target} was not contained in DB_CONFIG.')
        config = self.DB_CONFIG[target]
        return psycopg.connect(dbname=config['dbname'], user=user, password=config['user'][user],
                               host=config['host'], port=config['port'])

    @staticmethod
    def get_insert_values(table, data, skip_first=True):
        # Gather expected table columns
        table_cols = get_table_column_specs()[table][skip_first:]

        # Individual table modifications
        if table == 'drive_day':
            data['date'] = datetime.date.today().isoformat()
        elif table == 'event':
            data['creation_time'] = int(time.time() * 1000)
            table_cols = list(filter(lambda col: col[0] != 'event_index', table_cols))

        if table in ['electronics', 'dynamics', 'power']:
            data['event_id'] = os.getenv('EVENT_ID')

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
                                    RETURNING {get_table_column_specs()[table][0][0]}''', vals)
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
    logging.basicConfig(level=logging.NOTSET)
    get_table_column_specs(force=True, verbose=True)