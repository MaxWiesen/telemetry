import psycopg
import logging
import time
import numpy as np


class TableSpecs:
    table_column_specs = {  # Last Updated for DB schema v1.2
        'drive_day': {
            'day_id': {'type': int, 'range': (0, 1_000)},
            'time': {'type': float, 'range': (time.time(), time.time())},
            'conditions': {'type': str},
            'power_limit': {'type': np.float32, 'range': (0, 80_000)}
        },
        'event': {
            'event_id': {'type': int, 'range': (0, 1_000)},
            'creation_time': {'type': float, 'range': (time.time(), time.time())},
            'start_time': {'type': float, 'range': (time.time(), time.time())},
            'end_time': {'type': float, 'range': (time.time(), time.time())},
            'drive_day': {'type': int, 'range': (0, 1_000)},
            'driver': {'type': int, 'range': (0, 10)},
            'location': {'type': int, 'range': (0, 10)},
            'event_index': {'type': int, 'range': (0, 15)},
            'event_type': {'type': int, 'range': (0, 5)},
            # 'car_weight': {'type': np.float32, 'range': (100.0, 3_000)},
            'front_wing_on': {'type': bool},
            'regen_on': {'type': bool},
            # 'tow_angle': {'type': np.float32, 'range': (0, 22.5)},
            # 'camber': {'type': np.float32, 'range': (0, 0)},
            # 'ride_height': {'type': np.float32, 'range': (0, 0)},
            # 'ackerman_adjustment': {'type': np.float32, 'range': (0, 0)},
            'tire_pressue': {'type': np.float32, 'range': (10, 50)},
            # 'blade_arb_stiffness': {'type': np.float32, 'range': (0, 0)}
            # 'power_output': {'type': int, 'range': ()},
            # 'torque_output':  {'type': int, 'range': ()},
            # 'shock_dampening': {'type': int, 'range': ()},
            'rear_wing_on': {'type': bool},
            'undertray_on': {'type': bool}
        },
        'dynamics': {
            'event_id': {'type': int, 'range': (0, 1_000)},
            'time': {'type': float, 'range': (time.time(), time.time())},
            'body_acc_x': {'type': np.float64, 'range': (0, 4)},
            'body_acc_y': {'type': np.float64, 'range': (0, 4)},
            'body_acc_z': {'type': np.float64, 'range': (0, 4)},
            'body_ang_x': {'type': np.float64, 'range': (-180, 180)},
            'body_ang_y': {'type': np.float64, 'range': (-180, 180)},
            'body_ang_z': {'type': np.float64, 'range': (-180, 180)},
            'fr_acc_x': {'type': np.float64, 'range': (0, 4)},
            'fr_acc_y': {'type': np.float64, 'range': (0, 4)},
            'fr_acc_z': {'type': np.float64, 'range': (0, 4)},
            'fl_acc_x': {'type': np.float64, 'range': (0, 4)},
            'fl_acc_y': {'type': np.float64, 'range': (0, 4)},
            'fl_acc_z': {'type': np.float64, 'range': (0, 4)},
            'br_acc_x': {'type': np.float64, 'range': (0, 4)},
            'br_acc_y': {'type': np.float64, 'range': (0, 4)},
            'br_acc_z': {'type': np.float64, 'range': (0, 4)},
            'bl_acc_x': {'type': np.float64, 'range': (0, 4)},
            'bl_acc_y': {'type': np.float64, 'range': (0, 4)},
            'bl_acc_z': {'type': np.float64, 'range': (0, 4)},
            # 'torque_command': {'type': np.float64, 'range': ()},
            'motor_rpm': {'type': int, 'range': (0, 10_000)},
            'tire_temp': {'type': np.float64, 'range': (0, 500)},
            'brake_rotor_temp': {'type': np.float64, 'range': (0, 500)},
            'gps': {'type': 'point'}
        },
        'power': {
            # 'event_id': {'type': int, 'range': (0, 1_000)},
            'event_id': {'type': int, 'range': (1, 2)},
            'time': {'type': float, 'range': (time.time(), time.time())},
            'pack_voltage': {'type': np.float64, 'range': (0, 1_000)},
            'pack_current': {'type': np.float64, 'range': (0, 1_000)},
            'dcdc_current': {'type': np.float64, 'range': (0, 1_000)},
            'ambient_temp': {'type': np.float64, 'range': (0, 200)},
            'bms_pack_temp': {'type': np.float64, 'range': (0, 300)},  # Array, jsonb, or scalar?
            'bms_balancing_temp': {'type': np.float64, 'range': (0, 300)},  # Array, jsonb, or scalar?
            'contactor_status': {'type': bool},
            'bms_cells_v': {'type': np.empty((3, 3), np.float32), 'range': (0, 10)},
            'fan_speed': {'type': np.int64, 'range': (0, 10_000)},
            'inline_cooling_temp': {'type': np.float64, 'range': (-50, 300)},
            # 'cooling_flow': {'type': np.float64, 'range': ()}
        },
        'electronics': {
            'event_id': {'type': int, 'range': (0, 1_000)},
            'time': {'type': float, 'range': (time.time(), time.time())},
            'imd_on': {'type': bool},
            'hv_contactor_on': {'type': bool},
            'pre_c_contactor_on': {'type': bool},
            # 'pcb_temps': {'type': },
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
