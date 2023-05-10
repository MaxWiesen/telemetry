import pandas as pd
import psycopg
import pickle
import time
import logging
import datetime


def get_table_column_specs(force=False, verbose=False):
    now = time.time()
    last_update, table_column_specs = pickle.load(open('DB_description.pkl', 'rb'))
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
        pickle.dump((now, table_column_specs), open('DB_description.pkl', 'wb'))
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
            'host': 'localhost',
            'port': 5432
        }
    }

    def connect(self, target='PROD', user='analysis'):
        if target not in self.DB_CONFIG:
            raise ValueError(f'Target server {target} was not contained in DB_CONFIG.')
        config = self.DB_CONFIG[target]
        return psycopg.connect(dbname=config['dbname'], user=user, password=config['user'][user],
                               host=config['host'], port=config['port'])


if __name__ == '__main__':
    logging.basicConfig(level=logging.NOTSET)
    get_table_column_specs(force=True, verbose=True)