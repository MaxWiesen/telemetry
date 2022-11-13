from paho.mqtt import client as mqtt_client
import time
import math
import json


def main():
    client = mqtt_client.Client("paho-client")
    client.connect('localhost')
    count = 1
    while True:
        time.sleep(1)
        # obj = {'val': math.sin(time.time() * .5)}
        obj = {'creation_time': int(time.time() * 1000000), 'val': math.sin(time.time() * .5)}
        client.publish('paho_test', json.dumps(obj, indent=4))
        print(f'Outputting sine val ({obj["val"]}) now...')
        count += 1

if __name__ == '__main__':
    main()
