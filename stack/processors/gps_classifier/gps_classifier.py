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
import warnings

warnings.simplefilter('ignore', np.linalg.LinAlgError)



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
        print("DB OBJ: ", db_obj)
        #! Will crash if no event
        DBHandler.insert(table="classifier", data=db_obj, target=DBTarget.LOCAL, user="electric", handler=self.handler)
        self.current_process = None
        
    def _detect_events(self, points: NDArray, la_threshold: float, t_threshold: float, la_time_window: float, t_time_window: float, check_delay: int):
        """
        Detects for start of linear acceleration or turn events and calls associated functions
        ARGS:
            handler: active handler to call database
            points: array containing torque request, steer voltage, and time info
            la_threshold: threshold for the slope of the linear regression of torque request to trigger an event
            t_threshold: threshold for the slope of the linear regression of steer voltage to trigger an event
            la_time_window: linear acceleration time window to confirm a linear acceleration event (s)
            t_time_window: turn time window to confirm a turn event (s)
            check_delay: delay between each event starts (s)
        """
        
        torque_request = points[:, 1]
        steer_v = points[:, 2]
        time = points[:, 3]
        packet = points[:, 4]
        
        # Not enough time between event starts
        if len(self.processes) > 0 and time[0] < self.processes[-1].starting_time + check_delay * 1000:
            return
        
        # Look for high spike in torque request
        if not self.current_process or self.current_process.type != ProcessType.LINEAR_ACCELERATION:
            # smoothed_torque_request = np.polyfit(time, torque_request, 1)
            
            # if smoothed_torque_request[0] > la_threshold:
            #     starting_packet: int = packet[-1]
            #     starting_time: int = time[-1]
            #     print("STARTING TIME: ", starting_time)
            #     logging.info(f"HIGH TORQUE REQUEST ACHIEVED AT {starting_time}: {smoothed_torque_request[0]}")
            #     target_time = starting_time + la_time_window * 1000
            #     new_process = Process(type=ProcessType.LINEAR_ACCELERATION, starting_packet=starting_packet, starting_time=starting_time, target_time=target_time)
            #     self.processes.append(new_process)
            #     return
            # logging.info(f"HIGH TORQUE REQUEST NOT ACHIEVED: {smoothed_torque_request[0]}. TRASHING RESULTS")
            
            avg_torque_request = np.average(torque_request)
            
            if avg_torque_request > la_threshold:
                starting_packet: int = packet[-1]
                starting_time: int = time[-1]
                logging.info(f"STARTING TIME: {starting_time}")
                logging.info(f"HIGH TORQUE REQUEST ACHIEVED AT {starting_time}: {avg_torque_request}")
                target_time = starting_time + la_time_window * 1000
                new_process = Process(type=ProcessType.LINEAR_ACCELERATION, starting_packet=starting_packet, starting_time=starting_time, target_time=target_time)
                self.processes.append(new_process)
                return
            logging.info(f"HIGH TORQUE REQUEST NOT ACHIEVED: {avg_torque_request}. TRASHING RESULTS")

                
        # Look for high spike in steer voltage
        if not self.current_process or self.current_process.type != ProcessType.TURN:
            # smoothed_steer_voltage = np.polyfit(time, steer_v, 1)
            
            # if smoothed_steer_voltage[0] > t_threshold:
            #     starting_packet: int = packet[-1]
            #     starting_time: int = time[-1]
            #     logging.info(f"HIGH STEER REQUEST ACHIEVED AT {starting_time}: {smoothed_steer_voltage[0]}")
            #     target_time = starting_time + t_time_window * 1000
            #     new_process = Process(type=ProcessType.TURN, starting_packet=starting_packet, starting_time=starting_time, target_time=target_time)
            #     self.processes.append(new_process)
            #     return
            # logging.info(f"HIGH STEER REQUEST NOT ACHIEVED: {smoothed_steer_voltage[0]}. TRASHING RESULTS")
            
            avg_steer_voltage = np.average(steer_v) - 1.25 # 1.25 = center
            
            if abs(avg_steer_voltage) > t_threshold:
                starting_packet: int = packet[-1]
                starting_time: int = time[-1]
                logging.info(f"HIGH STEER REQUEST ACHIEVED AT {starting_time}: {avg_steer_voltage}")
                target_time = starting_time + t_time_window * 1000
                new_process = Process(type=ProcessType.TURN, starting_packet=starting_packet, starting_time=starting_time, target_time=target_time)
                self.processes.append(new_process)
                return
            logging.info(f"HIGH STEER REQUEST NOT ACHIEVED: {avg_steer_voltage}. TRASHING RESULTS")
        
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
            logging.info(f"LOADED PROCESS {self.current_process.type} STARTING AT {self.current_process.starting_time}")
            while True:
                points = np.array(DBHandler.simple_select(f"""
                    WITH next_time AS (
                        SELECT MIN(time) as min_time
                        FROM packet
                        WHERE time > {self.current_process.target_time}
                    )
                    SELECT d.gps_heading, d.body3_accel, p.time
                    FROM dynamics d
                    JOIN packet p ON p.packet_id = d.packet_id
                    WHERE (SELECT min_time FROM next_time) IS NOT NULL
                    AND p.time <= (SELECT min_time FROM next_time)
                    And p.time >= {self.current_process.starting_time}
                    ORDER BY p.time
                    ASC
                    LIMIT 500
                    """, handler=self.handler, target=DBTarget.LOCAL), dtype=object)
                if points.any(): break
                sleep(1 / frequency)
                
            logging.info(f"ALL POINTS FOUND. STARTING PROCESSING.")
            
            body3_accel = points[:, 1]
            body3_accel = np.array([list(row) for row in body3_accel])
            tangential_accel = body3_accel[:, 0]
            normal_accel = body3_accel[:, 1]
            heading = np.asarray(points[:, 0], dtype=np.float64)
            time = np.asarray(points[:, 2], dtype=np.float64)
            
            if self.current_process and self.current_process.type == ProcessType.LINEAR_ACCELERATION:
                smoothed_normal_accel = np.polyfit(time, normal_accel, 1)
                smoothed_heading = np.polyfit(time, heading, 1)
                if smoothed_normal_accel[0] > t_na_threshold or smoothed_heading[0] > t_h_threshold:
                    self._stop_process(self.current_process.starting_time)
                    logging.info(f"THRESHOLD EXCEEDED")
                else:
                    logging.info(f"THRESHOLD NOT EXCEEDED. TRASHING INSTANCE.")
                    

            
            if self.current_process and self.current_process.type == ProcessType.TURN:
                smoothed_tangential_accel = np.polyfit(time, tangential_accel, 1)
                if smoothed_tangential_accel[0] > la_threshold:
                    self._stop_process(self.current_process.starting_time)
                    logging.info(f"THRESHOLD EXCEEDED")
                else:
                    logging.info(f"THRESHOLD EXCEEDED")
                    logging.info(f"THRESHOLD NOT EXCEEDED. TRASHING INSTANCE.")
                    
                    
   
    def run_thread(self, frequency: int, window_size: int, la_threshold: float, t_threshold: float, la_time_window: float, t_time_window: float, debug=True):
        """Sliding Window"""
        
        while True:
            # Event not properly set
            if not debug and (not self.event_id or self.status != 1):
                logging.info("No Event Started")
                sleep(1 / frequency)
                continue
            
            # Not enough points
            if not debug and len(points) < window_size:
                logging.warning("Not enough points for computation. Trashing the instance")
                sleep(1 / frequency)
                continue
            
            # Suspicious time deltas
            MAX_TIME_DELTA = 5 * 1000
            if not debug and points[len(points) - 1][1] - points[0][1] < MAX_TIME_DELTA:
                logging.error(f"Interval is suspicious: {points[len(points) - 1][1] - points[0][1]}ms. Trashing the instance")
                sleep(1 / frequency)
                continue
            
            # logging.info(self.start_packet)
            points  = np.array(DBHandler.simple_select(f"SELECT d.gps_velocity, d.torque_request, c.steer_v, p.time, p.packet_id FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id JOIN controls c ON c.packet_id = d.packet_id WHERE d.packet_id >= {self.start_packet} ORDER BY d.packet_id ASC LIMIT {window_size}", handler=self.handler, target=DBTarget.LOCAL))
            # logging.info(points[0][3])
            
            if len(points) > 0:
                # Checks if at rest
                if abs(points[:, 0].mean()) < self.VELOCITY_THRESHOLD:
                    sleep(1 / frequency)
                    self._stop_process(points[:, 3][-1])
                else:
                    self._detect_events(points=points, la_threshold=la_threshold, t_threshold=t_threshold, la_time_window=la_time_window, t_time_window=t_time_window, check_delay=2)
                # increment window by half size
                self.start_packet = points[int(len(points) / 2)][4]

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
        
        #! Need to change these values
        frequency = 500
        window_size = 50
        la_threshold = 8
        t_threshold=0.4
        la_time_window=10
        t_time_window=10
        t1 = threading.Thread(target=processor.run_thread, args=(frequency, window_size, la_threshold, t_threshold, la_time_window, t_time_window))
        t1.start()
        
        #! Need to change these values
        frequency = 100
        la_threshold = 1
        t_na_threshold = 1
        t_h_threshold = 1
        t2 = threading.Thread(target=processor.process_thread, args=(frequency, la_threshold, t_na_threshold, t_h_threshold))
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