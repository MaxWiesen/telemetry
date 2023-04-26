import psycopg
import logging
import time
import numpy as np
import datetime


class TableSpecs:
    table_column_specs = {  # Last Updated for DB schema v1.2
        'drive_day': {
            'day_id': {'type': int, 'range': (0, 1_000)},
            'conditions': {'type': str},
            'power_limit': {'type': int, 'range': (0, 80_000)},
            'date': {'type': datetime.datetime, 'range': (datetime.date.today().isoformat(), datetime.date.today().isoformat())},

        },
        'event': {
            'event_id': {'type': int, 'range': (0, 1_000)},
            'drive_day': {'type': int, 'range': (0, 1_000)},
            'creation_time': {'type': float, 'range': (time.time(), time.time())},
            'start_time': {'type': float, 'range': (time.time(), time.time())},
            'end_time': {'type': float, 'range': (time.time(), time.time())},
            'car_id': {'type': int, 'range': (0, 2)},
            'driver_id': {'type': int, 'range': (0, 4)},
            'location_id': {'type': int, 'range': (0, 8)},
            'event_type': {'type': int, 'range': (0, 5)},
            'event_index': {'type': int, 'range': (0, 15)},
            'car_weight': {'type': np.float32, 'range': (100.0, 3_000)},
            'tow_angle': {'type': np.float32, 'range': (0, 22.5)},
            'camber': {'type': np.float32, 'range': (0, 0)},
            'ride_height': {'type': np.float32, 'range': (0, 0)},
            'ackerman_adjustment': {'type': np.float32, 'range': (0, 0)},
            'power_output': {'type': int, 'range': ()},
            'torque_output':  {'type': int, 'range': ()},
            'shock_dampening': {'type': int, 'range': ()},
            'frw_pressure': {'type': float, 'range': (0, 100)},
            'flw_pressure': {'type': float, 'range': (0, 100)},
            'brw_pressure': {'type': float, 'range': (0, 100)},
            'blw_pressure': {'type': float, 'range': (0, 100)},
            'front_wing_on': {'type': bool},
            'rear_wing_on': {'type': bool},
            'regen_on': {'type': bool},
            'undertray_on': {'type': bool}
        },
        'dynamics': {
            'time': {'type': float, 'range': (time.time(), time.time())},
            'frw_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'flw_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'brw_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'blw_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'body1_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'body1_ang': {'type': np.empty(3, float), 'range': (0, 5)},
            'body2_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'body2_ang': {'type': np.empty(3, float), 'range': (0, 5)},
            'body3_acc': {'type': np.empty(3, float), 'range': (0, 5)},
            'body3_ang': {'type': np.empty(3, float), 'range': (0, 5)},
            'accel_pedal_pos': {'type': float, 'range': (0, 5)},
            'brake_pressure': {'type': float, 'range': (0, 5)},
            'motor_rpm': {'type': int, 'range': (0, 10_000)},
            'torque_command': {'type': np.float64, 'range': (0, 100)},
            'gps': {'type': 'point'}
        },
        'power': {
            'time': {'type': int, 'range': (time.time(), time.time())},
            'bms_cells_v': {'type': np.empty(3, np.float32), 'range': (0, 10)},
            'pack_voltage': {'type': np.float64, 'range': (0, 1_000)},
            'pack_current': {'type': np.float64, 'range': (0, 1_000)},
            'lv_cells_v': {'type': np.empty(3, np.float32), 'range': (0, 10)},
            'lv_voltage': {'type': np.float64, 'range': (0, 1_000)},
            'lv_current': {'type': np.float64, 'range': (0, 1_000)},
            'ambient_temp': {'type': np.float64, 'range': (0, 200)},
            'bms_pack_temp': {'type': np.empty(3, np.float32), 'range': (0, 10)},  # Array, jsonb, or scalar?
            'bms_balancing_temp': {'type': np.empty(3, np.float32), 'range': (0, 10)},  # Array, jsonb, or scalar?
            'fan_speed': {'type': np.empty(3, np.float32), 'range': (0, 10)},
            'inline_cooling_temp': {'type': np.float64, 'range': (-50, 300)},
            'cooling_flow': {'type': np.float64, 'range': (0, 10)}
        },
        'electronics': {
            'time': {'type': int, 'range': (time.time(), time.time())},
            'imd_on': {'type': bool},
            'hv_contactor_on': {'type': bool},
            'pre_c_contactor_on': {'type': bool},
            'ls_contactor_on': {'type': bool},
            'lv_battery_status': {'type': int, 'range': (0, 5)}
        }
    }


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

    # def __init__(self):
        

    def connect(self, target='PROD', user='analysis'):
        if target not in self.DB_CONFIG:
            raise ValueError(f'Target server {target} was not contained in DB_CONFIG.')
        config = self.DB_CONFIG[target]
        return psycopg.connect(dbname=config['dbname'], user=user, password=config['user'][user],
                               host=config['host'], port=config['port'])

    @staticmethod
    def kill(cnx, commit=True):
        if commit:
            cnx.commit()
        if not cnx.closed:
            cnx.close()
        else:
            logging.info('An attempt was made to kill a closed connection.')


if __name__ == '__main__':
    try:
        handler = DBHandler()
        cnx = handler.connect(user='electric')
        with cnx.cursor() as cur:
            cur.execute(f"INSERT INTO event (creation_time) VALUES ('{datetime.datetime.now()}') RETURNING event_id")
            print(cur.fetchone())
    except Exception as e:
        raise e
    finally:
        DBHandler.kill(cnx)