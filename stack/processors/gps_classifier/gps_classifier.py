import json
import os
import logging
from time import sleep
import time
import pandas as pd
import numpy as np
from paho.mqtt import client as mqtt_client
import threading
import math
from psycopg import logger
import requests
from enum import Enum
from numpy.typing import NDArray


if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, DBTarget, get_table_column_specs    # Cheesed import statement using bind mount
    from mqtt_handler import MQTTHandler
else:
    from analysis.sql_utils.db_handler import DBHandler, DBTarget, get_table_column_specs
    from stack.ingest.mqtt_handler import MQTTHandler

# Linear acceleration, turns

class ProcessType(Enum):
    LINEAR_ACCELERATION = 0
    TURN = 1
    
class Process:
    def __init__(self, type: ProcessType, starting_packet: int, starting_time: int, target_time: int):
        self.type: ProcessType = type
        self.starting_packet: int = starting_packet
        self.starting_time: int = starting_time
        self.target_time: int = target_time
        
    
class GPSClassifierProcessor:
    def __init__(self, db_handler: DBHandler=None):
        self.handler = db_handler if db_handler else DBHandler()
        self.event_id = None
        self.start_packet: int = 0
        self.status = 0
        
        
        self.VELOCITY_THRESHOLD: float = 20
        
        self.current_process: Process | None = None
        self.processes: list[Process] = []
        
    def _stop_process(self, time: int):
        """
        Kills any ongoing process and adds data to classifier table
        ARGS:
            time: the end time of the event
        """
        process_to_end = self.current_process
        if process_to_end == None:
            return
        
        db_obj = {
                "event_id": self.event_id,
                "type": "trajectory",
                "start_time": process_to_end.starting_time,
                "end_time": time,
                "notes": f"{process_to_end.type.name}"
        }
        DBHandler.insert(table="classifier", data=db_obj, target=DBTarget.LOCAL, user="electric", handler=self.handler)
        self.current_process = None
        
    def _detect_events(self, points: NDArray, la_threshold: float, t_threshold: float, la_time_window: float, t_time_window: float):
        """
        Detects for start of linear acceleration or turn events and calls associated functions
        ARGS:
            handler: active handler to call database
            points: array containing torque request, steer voltage, and time info
            la_threshold: threshold for the slope of the linear regression of torque request to trigger an event
            t_threshold: threshold for the slope of the linear regression of steer voltage to trigger an event
            la_time_window: linear acceleration time window to confirm a linear acceleration event (s)
            t_time_window: turn time window to confirm a turn event (s)
        """
        
        torque_request = points[:, 1]
        steer_v = points[:, 2]
        time = points[:, 3]
        packet = points[:, 4]
        
        # Look for high spike in torque request
        if not self.current_process or self.current_process.type != ProcessType.LINEAR_ACCELERATION:
            smoothed_torque_request = np.polyfit(time, torque_request, 1)
             
            if smoothed_torque_request[0] > la_threshold:
                starting_packet: int = packet[-1]
                starting_time: int = time[-1]
                target_time = starting_time + la_time_window * 1000
                new_process = Process(type=ProcessType.LINEAR_ACCELERATION, starting_packet=starting_packet, starting_time=starting_time, target_time=target_time)
                self.processes.append(new_process)
                return
                
        # Look for high spike in steer voltage
        if not self.current_process or self.current_process.type != ProcessType.TURN:
            smoothed_steer_voltage = np.polyfit(time, steer_v, 1)
            
            if smoothed_steer_voltage[0] > t_threshold:
                starting_packet: int = packet[-1]
                starting_time: int = time[-1]
                target_time = starting_time + t_time_window * 1000
                new_process = Process(type=ProcessType.TURN, starting_packet=starting_packet, starting_time=starting_time, target_time=target_time)
                self.processes.append(new_process)
                return
        
    def process_thread(self, frequency: int, la_threshold: float, t_na_threshold: float, t_h_threshold: float):
        """
        Sequentially handles processes from the class list
        ARGS:
            handler: active handler to call database
            frequency: frequency to run the functino at
            la_h_threshold: threshold for linear acceleration 
        """
        
        while True:
            if len(self.processes) == 0:
                sleep(1 / frequency)
                continue
            
            self.current_process = self.processes[0]
            self.processes.pop(0)
            points: NDArray = []
            while True:
                points = np.array(DBHandler.simple_select("""
                    WITH next_time AS (
                        SELECT MIN(time) as min_time
                        FROM packet
                        WHERE time > {self.current_process.target_time}
                    )
                    SELECT d.gps_heading, d.body3_accel, p.time
                    FROM dynamics d
                    JOIN packet p ON p.packet_id = d.packet_id
                    WHERE (SELECT min_time FROM next_time) IS NOT NUL
                    AND p.time <= (SELECT min_time FROM next_time)
                    And p.time >= {self.current_process.starting_time}
                    ORDER BY p.time
                    LIMIT 500
                    """, handler=self.handler, target=DBTarget.LOCAL))
                if points != None: break
                sleep(1 / frequency)
            
            body3_accel = points[:, 1]
            tangential_accel = body3_accel[:, 0]
            normal_accel = body3_accel[:, 1]
            heading = points[:, 0]
            time = points[:, 2]
            
            if self.current_process.type == ProcessType.LINEAR_ACCELERATION:
                smoothed_normal_accel = np.polyfit(time, normal_accel, 1)
                smoothed_heading = np.polyfit(time, heading, 1)
                if smoothed_normal_accel[0] > t_na_threshold or smoothed_heading[0] > t_h_threshold:
                    self._stop_process(self.current_process.starting_time)

            
            if self.current_process.type == ProcessType.TURN:
                smoothed_tangential_accel = np.polyfit(time, tangential_accel, 1)
                if smoothed_tangential_accel[0] > la_threshold:
                    self._stop_process(self.current_process.starting_time)
                    
                
            
            
            
   
    def run_thread(self, frequency: int, window_size: int):
        """Sliding Window"""
        
        while True:
            # Event not properly set
            if not self.event_id or self.status != 1:
                logging.info("No Event Started")
                sleep(1 / frequency)
                continue
            
            # Not enough points
            if len(points) < window_size:
                logging.warning("Not enough points for computation. Trashing the instance")
                sleep(1 / frequency)
                continue
            
            # Suspicious time deltas
            MAX_TIME_DELTA = 5 * 1000
            if points[len(points) - 1][1] - points[0][1] < MAX_TIME_DELTA:
                logging.error(f"Interval is suspicious: {points[len(points) - 1][1] - points[0][1]}ms. Trashing the instance")
                sleep(1 / frequency)
                continue
            
            points  = np.array(DBHandler.simple_select(f"SELECT d.gps_velocity, d.torque_request, c.steer_v, p.time FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id JOIN controls c ON c.packet_id = d.packet_id WHERE d.packet_id >= {self.start_packet} ORDER BY d.packet_id DESC LIMIT {window_size}", handler=self.handler, target=DBTarget.LOCAL))
            # [0]: gps_velocity, [1]: gps_heading, [2]: body3_accel(pdu), [3]: torque_request, 
            
            # Checks if at rest
            if math.abs(points[:, 0].mean()) < self.VELOCITY_THRESHOLD:
                sleep(1 / frequency)
                self._stop_process(points[:, 3][-1])
                continue
            
            self._detect_events(points=points, la_threshold=1, t_threshold=1, la_time_window=10, t_time_window=10)
        
            sleep(1 / frequency)
        
    def on_message(self, client: mqtt_client.Client, userdata, msg):
        try:
            logging.info(f"MESSAGE HAS BEEN RECEIVED AT TOPIC {msg.topic}")
            if msg.topic == 'config/test':
                data = json.loads(msg.payload.decode())
                # Modify object variables
                self.event_id = data['event_id']
                self.status = data['status']
                if self.start_packet < data['start_packet']:
                    self.start_packet = data['start_packet']
        except json.JSONDecodeError:
            self.event_id = None
            self.status = None
            self.start_packet = None
    

        
def run_processor():
    with MQTTHandler(name="terence_dev") as mqtt:
        
        handler = DBHandler()
        processor = GPSClassifierProcessor(db_handler=handler)
        
        
        
        # Processing thread
        t1 = threading.Thread(target=processor.run_thread, args=(1, 50,))
        t1.start()
        
        t2 = threading.Thread(target=processor.process_thread, args=(1, 1, 1, 1))
        t2.start()
        
        mqtt.client.on_message = processor.on_message
        mqtt.subscribe("config/test")
        

# If Speed < threshold: trash results

# Linear Acceleration Event: 
#       - Followed by high torque request #!
#       - tangential acceleration > threshold (and then > 0) #!
#       - ∆speed > threshold (regression)
#       - normal acceleration < threshold, 
#       - ∆heading < threshold (regression), 

# Turn Event:
#       - normal acceleration > threshold #!
#       - ∆heading > threshold (regression)
#       - Steer voltage(?)

# Steps

# 2 threads

# 1. High Torque Request --> trigger listening event
# 2. Get x seconds worth of data after event triggered
# 3. a. If tangential acceleration's slope over threshold: confirm start of linear acceleration event & stop ongoing turn events
# 3. b. If not, trash it

# 1. High steer voltage --> trigger listening event
# 2. Get x seconds worth of data after event triggered
# 3. a. If high normal acceleration's slope (can be backed up by ∆heading): confirm turn event & stop ongoing linear acceleration event
# 3. b. If not, trash it


# Have a x seconds cooldown between event started, and start in parallel another check / add to queue