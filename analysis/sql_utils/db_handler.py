import pandas as pd
import psycopg
import pickle
import time
import logging
import datetime
import os


def get_table_column_specs(force=False, verbose=False):
    """
    Gets description of DB layout using either recent pkl file or request to database. Returns description in form of
    dict as follows: {'power': [('cooling_flow', <class 'float'>), (col2, type2), ...], table2: [...]}

    :param force:           bool determines whether or not to force refresh of cached description (pkl file)
    :param verbose:         bool used to pretty print most updated DB layout, only works if debugging level includes info

    :return db_description: dict represents current layout of DB--see function description for more explanation
    """
    #TODO: 1) Find underlying data types of ARRAY; 2) Add point type compatibility
    desc_path = './DB_description.pkl' if os.getenv('IN_DOCKER') else os.getcwd().rsplit('analysis/', 1)[0] + '/analysis/sql_utils/DB_description.pkl'
    if os.path.isfile(desc_path):
        last_update, table_column_specs = pickle.load(open(desc_path, 'rb'))
    else:
        force = True

    if not os.getenv('IN_DOCKER'):
        now = time.time()
        if force or now - last_update > 86_400 * 1:     # Days since last update
            data = DBHandler.simple_select("""SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE 
                                           FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'public'""",
                                           target='PROD', user='electric', return_type=pd.DataFrame)
            data.data_type.replace({'smallint': int, 'integer': int, 'bigint': int, 'real': float, 'text': str,
                                    'boolean': bool, 'date': datetime.date, 'ARRAY': list}, inplace=True)
            data.loc[data.column_name == 'date', 'data_type'] = str
            table_column_specs = {table: list(zip((table_data := data[data.table_name == table]).column_name,
                                                  table_data.data_type)) for table in data.table_name.unique()}
            pickle.dump((now, table_column_specs), open(desc_path, 'wb'))
            logging.info(f'\t\ttable_column_specs out of date and updated.')
        if verbose:     # Pretty print table column specs
            [logging.info(f'\t\t{table}\n' + ''.join([f'\n{col:^20} {str(dtype):^30}' for col, dtype in col_data]) +
                          '\n') for table, col_data in table_column_specs.items()]
    return table_column_specs


class DBHandler:
    """
    Class for interfacing with the database
    """
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
        """
        Creates psycopg.connection instance, pulling info from DB_CONFIG according to input target and user

        :param target:      str indicating target database server (according to DB_CONFIG)
        :param user:        str indicating what user to use to sign in to server

        :return conn:       psycopg.connection pointing at target, user and is used to generate cursors
        """
        if target not in self.DB_CONFIG:
            raise ValueError(f'Target server {target} was not contained in DB_CONFIG.')
        config = self.DB_CONFIG[target]
        return psycopg.connect(dbname=config['dbname'], user=user, password=config['user'][user],
                               host=config['host'], port=config['port'])

    @classmethod
    def simple_select(cls, query: str, target='PROD', user='electric', handler=None, return_type=None):
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
                return pd.io.sql.read_sql(query, cnx)

        with handler.connect(target, user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()

    @staticmethod
    def get_insert_values(table, data):
        """
        Collects data to be inserted into database. Accepts a target table and data payload, makes table-specific
        pre-processing changes, packages column names and values to be used in final insertion.

        :param table:       str indicating which table the insertion is targeting
        :param data:        dict dictionary containing column names and corresponding row values

        :return data:       dict containing preprocessed column name and values
        """
        # Gather expected table columns
        table_cols = get_table_column_specs()[table]

        # Individual table modifications
        if table == 'drive_day':
            data['date'] = datetime.date.today().isoformat()
            table_cols = list(filter(lambda col: col[0] != 'day_id', table_cols))
        elif table == 'event':
            data['creation_time'] = int(time.time() * 1000)
            table_cols = list(filter(lambda col: col[0] not in ['event_index', 'event_id'], table_cols))

        # Find columns missing from Flask app injection
        missing_cols = [col for col, _ in table_cols if col not in data]
        if missing_cols:
            logging.warning(f'\t\tFollowing columns were missing from transmitted data: {", ".join(missing_cols)}')

        # Separate NaNs and log
        table_cols = dict(table_cols)
        nan_vals = [val == 0 or bool(val) for _, val in data.items()]
        nans = {key: val for (key, val), nan in zip(data.items(), nan_vals) if not nan}
        data = {key: table_cols[key](val) for (key, val), nan in zip(data.items(), nan_vals) if nan}
        if nans:
            logging.warning(f'\t\tFollowing columns had NaN data: {str(nans).replace(": ", " = ")[1:-1]}')

        return data

    @classmethod
    def insert(cls, table, target='PROD', user='analysis', data=None, returning=None):
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

        if returning is None:
            returning = get_table_column_specs()[table][0][0]

        data = cls.get_insert_values(table, dict(data))

        with DBHandler().connect(target, user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(f'''INSERT INTO {table} ({', '.join(data.keys())})
                                    VALUES (%s{', %s' * (len(vals:=list(data.values())) - 1)}) 
                                    RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''',
                            vals)
                return cur.fetchone()[0] if isinstance(returning, str) else cur.fetchone()

    @classmethod
    def set_event_time(cls, event_id, target='PROD', user='analysis', start=True, returning=None):
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
                cur.execute(f'''UPDATE event SET {'start' if start else 'end'}_time = {now}
                                    WHERE event_id = {event_id}
                                    RETURNING {returning if isinstance(returning, str) else ', '.join(returning)}''')
                return cur.fetchone()[0] if isinstance(returning, str) else cur.fetchone()


if __name__ == '__main__':
    logging.basicConfig(level=logging.NOTSET)
    get_table_column_specs(force=True, verbose=True)