import pandas as pd
import pickle
import time
import logging
import datetime
import os
import psycopg
from psycopg.types.json import Jsonb
import sys
from pathlib import Path


class DBTarget:
    LOCAL = {
        'dbname': 'telemetry',
        'users': {
            'electric': '2fast2quick',
            'grafana': 'frontend',
            'analysis': 'north_dakota'
        },
        'host': 'db' if os.getenv('IN_DOCKER') else os.getenv('HOST_IP', 'localhost'),
        'port': 5432
    }
    PROD = {
        'dbname': 'telemetry',
        'users': {
            'electric': '2fast2quick',
            'grafana': 'frontend',
            'analysis': 'north_dakota'
        },
        'host': 'telemetry.servebeer.com',
        'port': 5432
    }

    @staticmethod
    def resolve_ip(ip):
        return {DBTarget[target]['host']: target for target in list(filter(lambda x: '__' not in x, dir(DBTarget)))}[ip]

    @staticmethod
    def resolve_target(target):
        try:
            return {target: DBTarget[target]['host'] for target in list(filter(lambda x: '__' not in x, dir(DBTarget)))}[target]
        except TypeError:
            return target['host']

def get_table_column_specs(force=False, verbose=False, target=DBTarget.LOCAL):
    """
    Gets description of DB layout using either recent pkl file or request to database. Returns description in form of
    dict as follows: {'power': {'cooling_flow': (<class 'float'>, 0), col2: (type2, num_dimension), ...}, table2: {...}}

    :param force:           bool determines whether to force refresh of cached description (pkl file)
    :param verbose:         bool used to pretty print most updated DB layout, only works if debugging level includes info
    :param target:          str  One of DBHandler.DB_CONFIG known servers to pull from

    :return db_description: dict represents current layout of DB--see function description for more explanation
    """
    def find_db_description():
        print(str(Path(__file__).parents[2]))
        root_folder = 'analysis' if 'analysis' in (cwd := os.getcwd()) else '/LHR'
        for root, dirs, files in os.walk(f'{os.getcwd().rsplit(root_folder, 1)[0]}/{root_folder}'):
            for fol in dirs:
                if fol == 'DB_description.pkl':
                    os.rmdir(f'{root}/{fol}')
            for name in files:
                if name == 'DB_description.pkl':
                    return os.path.abspath(os.path.join(root, name))
        return None

    desc_path = '/ingest/DB_description.pkl' if os.getenv('IN_DOCKER') else find_db_description()
    force = force or not bool(desc_path)
    desc_path = desc_path or os.getcwd().rsplit('/analysis', 1)[0] + '/analysis/sql_utils/DB_description.pkl'

    if not force:
        last_update, table_column_specs = pickle.load(open(desc_path, 'rb'))

    now = time.time()
    if force or now - last_update > 86_400 * 1:     # Update if it has been more than X days since last update
        data = DBHandler.simple_select('''SELECT t.tablename, a.attname, a.attndims,
                                       format_type(a.atttypid, a.atttypmod) as data_type FROM pg_tables t 
                                       JOIN pg_attribute a on a.attrelid::regclass = t.tablename::regclass 
                                       WHERE t.schemaname = 'public' AND a.attnum > 0''',
                                       target=target, user='electric', return_df=pd.DataFrame, index_col='tablename')
        data.loc[:, 'data_type'] = data.data_type.str.split('[', regex=False).str[0]     # Split [] if exists for is_list
        data.loc[data.attname == 'gps', 'attndims'] = 1
        data.data_type.replace({'smallint': int, 'integer': int, 'bigint': int, 'real': float, 'double precision': float,
                                'text': str, 'boolean': bool, 'jsonb': Jsonb, 'date': datetime.date, 'bytea': bytearray},
                               inplace=True)
        table_column_specs = {table: {row.attname: (row.data_type, row.attndims) for _, row in
                                      data.loc[data.index == table].iterrows()} for table in data.index.unique()}
        pickle.dump((now, table_column_specs), open(desc_path, 'wb'))
        logging.info(f'\t\ttable_column_specs {"forcefully updated" if force else "out of date and updated"}.')

    if verbose:     # Pretty print table column specs
        [logging.info(f'\t\t{table}\n' + ''.join([f'\n{col:^20} {str(data_type) + ndims * "[]":^30}' for col, (data_type, ndims) in col_data.items()]) +
                      '\n') for table, col_data in table_column_specs.items()]
    return table_column_specs


class DBHandler:
    """
    Class for interfacing with the database
    """

    def connect(self, target=DBTarget.LOCAL, user='analysis'):
        """
        Creates psycopg.connection instance, pulling info from DB_CONFIG according to input target and user

        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server

        :return conn:       psycopg.connection pointing at target, user and is used to generate cursors
        """
        if isinstance(target, str):
            target = getattr(DBTarget, target)
        return psycopg.connect(dbname=target['dbname'], user=user, password=target['users'][user],
                               host=target['host'], port=target['port'])

    @classmethod
    def simple_select(cls, query: str, target=DBTarget.LOCAL, user='electric', handler=None, return_df=False, **pd_kwargs):
        """
        Simple, easy way to get data from database. ONLY USED FOR SELECTING

        :param query:       str SQL query to send to database
        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server
        :param handler:     DBHandler handler to use to send requests (made and discarded if not given)
        :param return_df:   bool indicating whether to return a dataframe or not

        :return:            list[tuple] | type returns result of query's fetchall as list of tuple rows or as return_type
        """
        if handler is None:
            handler = cls()

        if not isinstance(query, str):
            raise ValueError('Simple select function is not capable of taking non-string query input.')

        if 'SELECT' not in query.upper():
            raise ValueError('Simple select is built specifically for surveying data. Non-"SELECT" queries are prohibited.')

        if return_df:
            with handler.connect(target, user) as cnx:
                return pd.io.sql.read_sql(query, cnx, **pd_kwargs)

        with handler.connect(target, user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    @staticmethod
    def get_insert_values(table: str, data: dict, table_desc):
        """
        Collects data to be inserted into database. Accepts a target table and data payload, makes table-specific
        pre-processing changes, packages column names and values to be used in final insertion.

        :param table:       str indicating which table the insertion is targeting
        :param data:        dict dictionary containing column names and corresponding row values

        :return data:       dict containing preprocessed column name and values
        """
        # Individual table modifications
        if table == 'drive_day':
            data['date'] = datetime.date.today()
            table_desc.pop('day_id')
        elif table == 'event':
            data['creation_time'] = int(time.time() * 1000)
            map(table_desc.pop, ['event_index', 'event_id'])

        # Find columns missing from Flask app injection
        missing_cols = [col for col, (_, _) in table_desc.items() if col not in data]
        if missing_cols:
            logging.warning(f'\t\tFollowing columns were missing from transmitted data: {", ".join(missing_cols)}')

        # Separate NaNs and log
        nan_vals = [val == 0 or bool(val) for _, val in data.items()]
        nans = {key: val for (key, val), nan in zip(data.items(), nan_vals) if not nan}
        data = {key: val if key in ['date', 'gps', 'vcu_flags'] or isinstance(val, (list, bytearray)) else table_desc[key][0](val)
                     for (key, val), nan in zip(data.items(), nan_vals) if nan}
        if nans:
            logging.warning(f'\t\tFollowing columns had NaN data: {str(nans).replace(": ", " = ")[1:-1]}')

        return data

    @classmethod
    def insert(cls, table: str, target=DBTarget.LOCAL, user='analysis', data=None, returning=None):
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

        table_desc = get_table_column_specs(target=target)[table]

        if returning is None:
            returning = next(iter(table_desc.keys()))   # Use name of first column of table if not explicitly passed

        data = cls.get_insert_values(table, dict(data), table_desc)

        def flat_gen(data):
            # Dumb function to flatten dtype list to conform to psycopg requirements
            for col, vals in data.items():
                if col != 'gps':
                    yield vals
                else:
                    for val in vals: yield val

        dtype_map = {float: '%s', int: '%s', str: '%s', bool: '%s', list: '%s', Jsonb: '%s', datetime.date: '%s',
                     'point': 'point(%s, %s)', bytearray: '%s'}
        with DBHandler().connect(target, user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(f'''INSERT INTO {table} ({', '.join(data.keys())})
                            VALUES ({', '.join([dtype_map[table_desc[col][0]] for col in data.keys()])})
                            RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''',
                            list(flat_gen(data)))
                return cur.fetchone()[0] if isinstance(returning, str) else cur.fetchone()

    @staticmethod
    def set_event_status(event_id: int, status: int, target=DBTarget.LOCAL, user='analysis', packet_end=None, returning=None):
        """
        Targets an event_id and updates the start or end time, with ability to get columns from the affected row.

        :param event_id:    int event_id whose start/end time will be updated
        :param status:      int indicating event status (0 = completed, 1 = running, 2 = created and awaiting start)
        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server
        :param packet_end:  int indicating last packet contained in event
        :param returning:   str | list column names to return values for after request is executed

        :return data:       SQL_VALUE | tuple of values in order of returning
        """
        with DBHandler().connect(target, user) as cnx:
            with cnx.cursor() as cur:
                now = int(time.time() * 1000)
                if status == 1:
                    # Set event status to running
                    cur.execute(f'''UPDATE event SET start_time = {now}, status = 1
                                    WHERE event_id = {event_id}
                                    RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''')
                elif status == 0:
                    # Signal end of event and update final packet
                    if packet_end is None:
                        raise ValueError('Packet end argument was none while ending event.')
                    cur.execute(f'''UPDATE event SET end_time = {now}, status = 0, packet_end = {packet_end}
                                    WHERE event_id = {event_id}
                                    RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''')
                else:
                    # Used for recording less than 0 status (error) codes
                    cur.execute(f'''UPDATE event SET status = {status} WHERE event_id = {event_id}
                                    RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''')
                return cur.fetchone()[0] if isinstance(returning, str) else cur.fetchone()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    get_table_column_specs(False, True, 'LOCAL')
