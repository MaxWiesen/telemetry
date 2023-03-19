import psycopg
from datetime import datetime
from analysis.database.sql_utils.db_handler import DBHandler


class Injector:
    # def __init__(self, **kwargs):



    @staticmethod
    def create_drive_day(**kwargs):
        cnx = DBHandler().connect()
        try:
            cur = cnx.cursor()
            cur.execute(f'''INSERT INTO drive_day (time, conditions, power_limit)
                            VALUES ({datetime.now()}, {kwargs.get("conditions")}, {kwargs.get("power_limit")})
                            RETURNING day_id''')
            DBHandler.kill(cnx)
            return cur.fetchone()[0]
        except Exception as e:
            raise e
        finally:
            DBHandler.kill(cnx)

# if __name__ == '__main__':
#     main()