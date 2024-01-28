import pandas as pd
import pickle
import time
import logging
import datetime
import os
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb


def get_table_column_specs(force=False, verbose=False):
    """
    Gets description of DB layout using either recent pkl file or request to database. Returns description in form of
    dict as follows: {'power': {'cooling_flow': (<class 'float'>, False), col2: (type2, is_list2), ...}, table2: {...}}

    :param force:           bool determines whether to force refresh of cached description (pkl file)
    :param verbose:         bool used to pretty print most updated DB layout, only works if debugging level includes info

    :return db_description: dict represents current layout of DB--see function description for more explanation
    """
    desc_path = './DB_description.pkl' if os.getenv('IN_DOCKER') else os.getcwd().rsplit('analysis/', 1)[0] + '/analysis/sql_utils/DB_description.pkl'

    force = force or not Path(desc_path).is_file()      # force true if force or the DB_description.pkl file DNE
    if not force:
        last_update, table_column_specs = pickle.load(open(desc_path, 'rb'))

    now = time.time()
    if force or now - last_update > 86_400 * 1:     # Update if it has been more than X days since last update
        data = DBHandler.simple_select('''SELECT t.tablename, a.attname, 
                                       format_type(a.atttypid, a.atttypmod) as data_type FROM pg_tables t 
                                       JOIN pg_attribute a on a.attrelid::regclass = t.tablename::regclass 
                                       WHERE t.schemaname = 'public' AND a.attnum > 0''',
                                       target='PROD', user='electric', return_type=pd.DataFrame, index_col='tablename')
        data[['data_type', 'is_list']] = data.data_type.str.rsplit('[]', expand=True)     # Split [] if exists for is_list
        data.loc[data.attname == 'gps', 'is_list'] = ''
        data.loc[:, 'is_list'] = data.is_list == ''
        data.data_type.replace({'smallint': int, 'integer': int, 'bigint': int, 'real': float, 'double precision': float,
                                'text': str, 'boolean': bool, 'jsonb': Jsonb, 'date': datetime.date}, inplace=True)
        table_column_specs = {table: {row.attname: (row.data_type, row.is_list) for _, row in
                                      data.loc[data.index == table].iterrows()} for table in data.index.unique()}
        pickle.dump((now, table_column_specs), open(desc_path, 'wb'))
        logging.info(f'\t\ttable_column_specs {"forcefully updated" if force else "out of date and updated"}.')

    if verbose:     # Pretty print table column specs
        [logging.info(f'\t\t{table}\n' + ''.join([f'\n{col:^20} {str(data_type) + is_list * "[]":^30}' for col, (data_type, is_list) in col_data.items()]) +
                      '\n') for table, col_data in table_column_specs.items()]
    return table_column_specs


class DBHandler:
    """
    Class for interfacing with the database
    """
    DB_CONFIG = {
        'PROD': {
            'dbname': 'telemetry',
            'users': {
                'electric': '2fast2quick',
                'grafana': 'frontend',
                'analysis': 'north_dakota'
            },
            'host': 'db' if os.getenv('IN_DOCKER') else 'localhost',
            'port': 5432
        }
    }

    def connect(self, target='PROD', user='analysis'):
        """
        Creates psycopg.connection instance, pulling info from DB_CONFIG according to input target and user

        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server

        :return conn:       psycopg.connection pointing at target, user and is used to generate cursors
        """
        if target not in self.DB_CONFIG:
            raise ValueError(f'Target server {target} was not contained in DB_CONFIG.')
        config = self.DB_CONFIG[target]
        return psycopg.connect(dbname=config['dbname'], user=user, password=config['users'][user],
                               host=config['host'], port=config['port'])

    @classmethod
    def simple_select(cls, query: str, target='PROD', user='electric', handler=None, return_type=None, **pd_kwargs):
        """
        Simple, easy way to get data from database. ONLY USED FOR SELECTING

        :param query:       str SQL query to send to database
        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server
        :param handler:     DBHandler handler to use to send requests (made and discarded if not given)
        :param return_type: type used to determine what type to return data in

        :return:            list[tuple] | type returns result of query's fetchall as list of tuple rows or as return_type
        """
        if handler is None:
            handler = cls()

        if not isinstance(query, str):
            raise ValueError('Simple select function is not capable of taking non-string query input.')

        if 'SELECT' not in query.upper():
            raise ValueError('Simple select is built specifically for surveying data. Non-"SELECT" queries are prohibited.')

        if return_type is pd.DataFrame:
            with handler.connect(target, user) as cnx:
                return pd.io.sql.read_sql(query, cnx, **pd_kwargs)

        with handler.connect(target, user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    @staticmethod
    def get_insert_values(table: str, data: dict):
        """
        Collects data to be inserted into database. Accepts a target table and data payload, makes table-specific
        pre-processing changes, packages column names and values to be used in final insertion.

        :param table:       str indicating which table the insertion is targeting
        :param data:        dict dictionary containing column names and corresponding row values

        :return data:       dict containing preprocessed column name and values
        """
        # Gather expected table columns
        table_desc = get_table_column_specs()[table]

        # Individual table modifications
        if table == 'drive_day':
            data['date'] = datetime.date.today()
            table_desc.pop('day_id')
        elif table == 'event':
            data['creation_time'] = int(time.time() * 1000)
            [table_desc.pop(col) for col in ['event_index', 'event_id']]

        # Find columns missing from Flask app injection
        missing_cols = [col for col, (_, _) in table_desc.items() if col not in data]
        if missing_cols:
            logging.warning(f'\t\tFollowing columns were missing from transmitted data: {", ".join(missing_cols)}')

        # Separate NaNs and log
        nan_vals = [val == 0 or bool(val) for _, val in data.items()]
        nans = {key: val for (key, val), nan in zip(data.items(), nan_vals) if not nan}
        data = {key: table_desc[key][0](val) if key not in ['date', 'gps'] and not isinstance(val, list) else val
                     for (key, val), nan in zip(data.items(), nan_vals) if nan}
        if nans:
            logging.warning(f'\t\tFollowing columns had NaN data: {str(nans).replace(": ", " = ")[1:-1]}')

        return data

    @classmethod
    def insert(cls, table: str, target='PROD', user='analysis', data=None, returning=None):
        """
        Targets a table and sends an individual row of data to database, with ability to get columns from the last row.

        :param table:       str indicating which table the insertion is targeting
        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server
        :param data:        dict | request.* holds data to send to database
        :param returning:   str | list column names to return values for after request is executed

        :return data:       SQL_VALUE | tuple of values in order of returning
        """
        if data is None:
            raise ValueError('No data in payload.')

        table_desc = get_table_column_specs()[table]

        if returning is None:
            returning = next(iter(table_desc.keys()))   # Use name of first column of table if not explicitly passed

        data = cls.get_insert_values(table, dict(data))

        def flat_gen(data):
            # Dumb function to flatten dtype list to conform to psycopg requirements
            for col, vals in data.items():
                if col != 'gps':
                    yield vals
                else:
                    for val in vals: yield val

        dtype_map = {float: '%s', int: '%s', str: '%s', bool: '%s', list: '%s', Jsonb: '%s', datetime.date: '%s',
                     'point': 'point(%s, %s)'}
        with DBHandler().connect(target, user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(f'''INSERT INTO {table} ({', '.join(data.keys())})
                            VALUES ({', '.join([dtype_map[table_desc[col][0]] for col in data.keys()])})
                            RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''',
                            list(flat_gen(data)))
                return cur.fetchone()[0] if isinstance(returning, str) else cur.fetchone()

    @classmethod
    def set_event_time(cls, event_id: int, target='PROD', user='analysis', start=True, returning=None):
        """
        Targets an event_id and updates the start or end time, with ability to get columns from the affected row.

        :param event_id:    int event_id whose start/end time will be updated
        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server
        :param start:       bool indicates whether to set start or end time
        :param returning:   str | list column names to return values for after request is executed

        :return data:       SQL_VALUE | tuple of values in order of returning
        """
        now = int(time.time() * 1000)
        with DBHandler().connect(target, user) as cnx:
            with cnx.cursor() as cur:
                # Set start_/end_time
                cur.execute(f'''UPDATE event SET {'start' if start else 'end'}_time = {now} 
                                WHERE event_id = {event_id}
                                RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''')
                return cur.fetchone()[0] if isinstance(returning, str) else cur.fetchone()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    get_table_column_specs(True, True)
    # d = {'time': 19288, 'frw_acc': [99.0133716054641, 85.64651514227279, 31.696477091949284, 54.52213555162191, 54.2317917847808], 'flw_acc': [1.703249223495884, 13.023149593120708, 73.93942070096864, 95.99276140676814, 0.6369991788708562], 'brw_acc': [7.420226144130082, 13.822294911183286, 83.20297370455478, 10.289661327934308, 23.00130126023412], 'blw_acc': [73.4511903705272, 15.959505406213925, 90.17788150888789, 13.291596300229369, 4.424584938348475], 'body1_acc': [94.11942339562613, 84.47629271886635, 27.52693689142195, 84.60125031829965, 42.760604229844155], 'body1_ang': [65.98816195572515, 27.234856220926616, 52.35924496805096, 15.977586859108984, 51.84177096471721], 'body2_ang': [48.033919542956895, 88.11454221070423, 98.74227227107748, 81.88160455201, 29.3983623402709], 'body2_acc': [30.019065771313713, 91.0846544175037, 89.71441037885677, 26.212993887542403, 48.839396938308255], 'body3_acc': [69.85504273035421, 90.07982624300931, 28.816454241116052, 0.39004040978948273, 75.7664490320731], 'body3_ang': [21.374140726125745, 42.22324264727002, 37.93146289657039, 65.80943127904966, 29.02254001358343], 'accel_pedal_pos': 39.37028376348777, 'brake_pressure': 28.779001462661125, 'motor_rpm': 22081, 'torque_command': 20931, 'gps': [-63.41273639873167, -54.05523687471205]}
    # DBHandler.insert('dynamics', data=d, returning='gps')
    # print(DBHandler.insert(table='drive_day', target='PROD', user='electric', data={'date': datetime.date.today().isoformat(), 'power_limit': 75000, 'conditions': 'Testing'}, returning='day_id'))