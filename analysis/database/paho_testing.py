import numpy as np
from numpy.random import default_rng
import time
import pickle
import requests
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[2]))

from stack.ingest.mqtt_handler import mosquitto_connect
from analysis.sql_utils.db_handler import get_table_column_specs


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

    def get_random_data(self, dtype: type, size=1, as_scalar=False, **kwargs):
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
            res = [self.get_random_data(float, 1, as_scalar=True, low=-180, high=180),
                   self.get_random_data(float, 1, as_scalar=True, low=-90, high=90)]
        # If bool or int, use default_rng.integers method with some argument manipulation
        elif dtype is bool or np.issubdtype(dtype, np.integer):
            res = self.rng.integers(0, 2 if dtype is bool else 32767, size=size, dtype=dtype)
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

        return res[0] if size == 1 else list(res)


def main():
    client = mosquitto_connect('paho_tester')
    test = DataTester()
    table = 'dynamics'
    table_desc = get_table_column_specs()[table]

    payload = {}
    for i in range(100):
        for col, dtype, is_list in filter(lambda x: x[0] != 'event_id', table_desc):
            if dtype is float:
                payload[col] = test.get_random_data(dtype, min=0, max=100, size=5 if is_list else 1)
            else:
                payload[col] = test.get_random_data(dtype, size=5 if is_list else 1)

        print(f'Publishing payload #{i:>3}: {payload}')
        client.publish(f'data/{table}', pickle.dumps(payload))
        time.sleep(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    client = mosquitto_connect('paho_tester')
    client.publish('data/high_f', payload=pickle.dumps("{'accel_pedal_pos': 30.614096520766875, 'brake_pressure': 16.516149589439998, 'motor_rpm': 32599, 'torque_command': 4597, 'gps': [168.76390118707695, 24.883174273483775], 'imd_on': True, 'hv_contactor_on': True, 'pre_c_contactor_on': True, 'inline_cooling_temp': 53.21072278995247, 'cooling_flow': 89.06544233041728}"))
    client.disconnect()