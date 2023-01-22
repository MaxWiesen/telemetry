from paho.mqtt import client as mqtt_client
from numpy.random import default_rng
import time
import math
import json

# class DataTester:
    


def get_random_data(dtype, num, *minmax):
    rng = default_rng()
    if dtype is bool:
        return rng.integers(0, 2, size=num).astype(bool)
    return rng.integers(*minmax, size=num)


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
    print(get_random_data(bool, 10, 15))
