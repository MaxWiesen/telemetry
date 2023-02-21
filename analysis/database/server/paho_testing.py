import numpy as np
from paho.mqtt import client as mqtt_client
from numpy.random import default_rng
import time
import json
import requests

class DataTester:
    """
    Class for testing database with random values in correct data types.
    """
    def __init__(self, seed=None):
        """
        Initializes DataTester class by initiating a numpy.random.Generator.

        :param seed:        seed to pass to numpy.random.Generator constructor
        """
        self.rng = default_rng(seed)
        self.table_column_specs = {     # Last Updated for DB schema v1.2
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
                'drive_day':  {'type': int, 'range': (0, 1_000)},
                'driver':  {'type': int, 'range': (0, 10)},
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
                'bms_pack_temp': {'type': np.float64, 'range': (0, 300)},           # Array, jsonb, or scalar?
                'bms_balancing_temp': {'type': np.float64, 'range': (0, 300)},      # Array, jsonb, or scalar?
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

    def get_random_data(self, dtype: type, size=1, as_scalar=False, **kwargs):
        # TODO: Adapt for handling arrays (like 'bms_cells_v')
        """
        Creates and returns array of (pseudo-)randomly generated number based on given data type.

        :param dtype:       class indicating desired output data type
        :param size:        int indicating number of values desired
        :param as_scalar:   bool if true and size is 1, return value as scalar instead of list
        :param kwargs:      min/low: int indicating minimum value for rng
                            max/high: int indicating maximum value for rng
                            endpoint: bool indicating whether to include high/max value (note: only works for floats)
                            length: int indicating number of sentences (note: only works for strings)
        :return:            array of randomly generated numbers
        """

        # Checks if low/min was passed by name, but not high/max which would cause low/min to be treated as high/max
        if ('low' in kwargs or 'min' in kwargs) and 'high' not in kwargs and 'max' not in kwargs:
            raise ValueError('min/low number specified, but max/high number was not.')

        # Checks if as_scalar matches size. If size > 1, a scalar cannot contain the values
        if as_scalar and size != 1:
            raise ValueError('as_scalar was set to true, but more than 1 value was expected to be returned.')

        # If point, return a tuple of longitude and latitude
        if dtype == 'point':
            res = f'point({self.get_random_data(float, 1, as_scalar=True, low=-180, high=180)}, {self.get_random_data(float, 1, as_scalar=True, low=-90, high=90)})'
        # If bool or int, use default_rng.integers method with some argument manipulation
        elif dtype is bool or np.issubdtype(dtype, np.integer):
            res = self.rng.integers(low=2 if dtype is bool else low if isinstance((low := kwargs.get('low', kwargs.get('high'))), int) else kwargs.get('min', kwargs.get('max')),
                                    high=kwargs.get('high', kwargs.get('max')) if 'low' in kwargs and np.issubdtype(dtype, np.integer) else None,
                                    size=size, dtype=dtype)
        # If float, use default_rng.random method with [0, 1) --> [low/min, high/max) transformation algorithm
        elif np.issubdtype(dtype, np.floating):
            # Algorithm used is (big - small) * random(0-1) + small
            res = (kwargs.get('high', kwargs.get('max', 1)) - kwargs.get('low', kwargs.get('min', 0))) * \
                self.rng.random(size, dtype) + kwargs.get('low', kwargs.get('min', 0))
        # If str, bacon
        elif dtype is str:
            res = [requests.get('https://baconipsum.com/api/',
                                params={'type': 'meat-and-filler', 'sentences': kwargs.get('length', 10),
                                        'start-with-lorem': 1}).text[2:-2] for _ in range(size)]
        else:
            raise NotImplementedError(f'Data type {dtype} not implemented yet.')

        return res[0] if as_scalar else res


def main():
    client = mqtt_client.Client('paho-client')
    client.connect('10.0.0.21')
    test = DataTester()
    count = 1
    table = 'drive_day'
    while True:
        time.sleep(1)
        # obj = {'val': math.sin(time.time() * .5)}
        data = {KPI: test.get_random_data(vals['type'], 1, True, low=vals['range'][0], high=vals['range'][1]) if 'range' in vals else test.get_random_data(vals['type'], 1, True) for KPI, vals in test.table_column_specs[table].items()}
        data.update({key: int(val) for key, val in data.items() if type(val) is np.int64})
        print(data)
        client.publish('dynamics', json.dumps(data, indent=4))
        print(f'Pushing values ({data}) now...')
        count += 1


if __name__ == '__main__':
    # print(DataTester().get_random_data(float, size=1, min=10, max=100))
    # print(DataTester().get_random_data(str, size=10, length=10))
    main()