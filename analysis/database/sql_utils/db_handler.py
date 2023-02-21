import psycopg
import logging

class DBHandler:
    DB_CONFIG = {
        'PROD': {
            'dbname': 'telemetry',
            'user': {
                'electric': '2fast2quick',
                'grafana': 'frontend',
                'analysis': 'north_dakota'
            }
        }
    }

    # def __init__(self):
        

    def connect(self, target='PROD', user='analysis'):
        if target not in self.DB_CONFIG:
            raise ValueError(f'Target server {target} was not contained in DB_CONFIG.')
        return psycopg.connect(dbname=self.DB_CONFIG[target]['dbname'], user=user,
                               password=self.DB_CONFIG[target]['user'][user])

    @staticmethod
    def kill(conn):
        if not conn.closed:
            conn.close()
        else:
            logging.info('An attempt was made to kill a closed connection.')


if __name__ == '__main__':
    conn = DBHandler().connect()
    print(f'Conn closed 1: {conn.closed}')
    DBHandler.kill(conn)
    print(f'Conn closed 2: {conn.closed}')
    conn.close()
    print(f'Conn closed 3: {conn.closed}')
