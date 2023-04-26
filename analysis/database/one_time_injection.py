import datetime
import time
import logging
from analysis.database.sql_utils.db_handler import DBHandler, TableSpecs


class Injector:
    # def __init__(self, **kwargs):
    @staticmethod
    def get_insert_values(table, data, skip_first=True):
        # Individual table modifications
        if table == 'drive_day':
            data['date'] = datetime.date.today().isoformat()
        elif table == 'event':
            data['creation_time'] = int(time.time() * 1000)

        # Gather expected table columns
        table_cols = list(TableSpecs.table_column_specs[table].items())[int(skip_first):]

        # Find columns missing from Flask app injection
        missing_cols = [col for col, _ in table_cols if col not in data]
        if missing_cols:
            logging.warning(f'\t\tFollowing columns were missing from transmitted data: {", ".join(missing_cols)}')

        # Separate NaNs and log
        nan_vals = [val == 0 or bool(val) for key, val in data.items()]
        nans = {key: val for (key, val), nan in zip(data.items(), nan_vals) if not nan}
        data = {key: val for (key, val), nan in zip(data.items(), nan_vals) if nan}
        if nans:
            logging.warning(f'\t\tFollowing columns had NaN data: {str(nans).replace(": ", " = ")[1:-1]}')

        return ', '.join(data.keys()), list(data.values())

    @classmethod
    def create_from_table(cls, table, user='analysis', data=None):
        if data is None:
            raise ValueError('No data in payload.')

        cols, vals = cls.get_insert_values(table, dict(data))

        with DBHandler().connect(user=user) as cnx:
            with cnx.cursor() as cur:
                cur.execute(f'''INSERT INTO {table} ({cols}) VALUES (%s{', %s' * (len(vals) - 1)}) 
                                RETURNING {list(TableSpecs.table_column_specs[table].keys())[0]}''', vals)
                return cur.fetchone()[0]


if __name__ == '__main__':
    Injector.get_insert_values('drive_day')