import numpy as np
from paho.mqtt import client as mqtt_client
from numpy.random import default_rng
import time
import math
import json
import requests

class DataTester:
    """
    Class for testing database with random values in correct data types.
    """
    def __init__(self, seed=None):
        """
        Initializes DataTester class by initiating a numpy.random.Generator.

        :param seed:    seed to pass to numpy.random.Generator constructor
        """
        self.rng = default_rng(seed)
        self.table_column_specs = {
            'drive_day': {
                'day_id': {'type': int, 'range': (0, 1_000)},
                'conditions': {'type': str},
                # 'power_limit': {'type': np.float32, 'range': (0, 80_000)}
            },
            'event': {
                'event_id': {'type': int, 'range': (0, 1_000)},
                'creation_time': {'type': int, 'range': (time.time(), time.time())},
                'start_time': {'type': int, 'range': (time.time(), time.time())},
                'end_time': {'type': int, 'range': (time.time(), time.time())},
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
            'dynamcis': {
                'event_id': {'type': int, 'range': (0, 1_000)},
                'time': {'type': int, 'range': (time.time(), time.time())},
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
                'gps': {}
            }
        }

    def get_random_data(self, dtype: type, size=1, **kwargs):
        """
        Creates and returns array of (pseudo-)randomly generated number based on given data type.

        :param dtype:   class indicating desired output data type
        :param size:    int indicating number of values desired
        :param kwargs:  min/low: int indicating minimum value for rng
                        max/high: int indicating maximum value for rng
                        endpoint: bool indicating whether to include high/max value (note: only works for floats)
        :return:        array if randomly generated numbers
        """

        # Checks if low/min was passed by name, but not high/max which would cause low/min to be treated as high/max
        if ('low' in kwargs or 'min' in kwargs) and 'high' not in kwargs and 'max' not in kwargs:
            raise ValueError('min/low number specified, but max/high number was not.')

        # If bool or int, use default_rng.integers method with some argument manipulation
        if dtype is bool or np.issubdtype(dtype, np.integer):
            return self.rng.integers(low=2 if dtype is bool else kwargs.get('low', kwargs.get('high')) or kwargs.get('min', kwargs.get('max')),
                                     high=kwargs.get('high', kwargs.get('max')) if 'low' in kwargs and dtype is int else None,
                                     size=size, dtype=dtype)
        # If float, use default_rng.random method with [0, 1) --> [low/min, high/max) transformation algorithm
        elif np.issubdtype(dtype, np.floating):
            # Algorithm used is (big - small) * random(0-1) + small
            return (kwargs.get('high', kwargs.get('max', 1)) - kwargs.get('low', kwargs.get('min', 0))) * \
                self.rng.random(size, dtype) + kwargs.get('low', kwargs.get('min', 0))
        # If str, bacon
        elif dtype is str:
            return [requests.get('https://baconipsum.com/api/', params={'type': 'meat-and-filler', 'sentences': size,
                                                                        'start-with-lorem': 1}).text[2:-2]]
        else:
            raise NotImplementedError(f'Data type {dtype} not implemented yet.')


def main():
    client = mqtt_client.Client("paho-client")
    client.connect('localhost')
    count = 1
    while True:
        time.sleep(1)
        # obj = {'val': math.sin(time.time() * .5)}
        obj = {'creation_time': int(time.time() * 1000000), 'val': math.sin(time.time() * .5)}
        client.publish('drive_day', json.dumps(obj, indent=4))
        print(f'Outputting sine val ({obj["val"]}) now...')
        count += 1


if __name__ == '__main__':
    # print(DataTester().get_random_data(float, size=300, min=10, max=10000))
    print(DataTester().get_random_data(str, size=10))