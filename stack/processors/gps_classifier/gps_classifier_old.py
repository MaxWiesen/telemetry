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

class Trajectory(Enum):
    LINEAR = 0
    TURN_RIGHT = 1
    TURN_LEFT = 2
    SLOW = 3
    
class Motion(Enum):
    ACCELERATION = 0
    DECELERATION = 1
    SLOW = 2

class GPSClassifierProcessor:
    def __init__(self, db_handler: DBHandler=None):
        self.handler = db_handler if db_handler else DBHandler()
        self.event_id = None
        self.start_packet: int = 0
        self.status = 0
        
        self.trajectory: Trajectory = Trajectory.LINEAR
        self.motion: Motion = Motion.SLOW
        
        
        self.VELOCITY_THRESHOLD: float = 20
        

    def update_motion(self, motion: Trajectory, time: float):
        # Trigger event
        if motion != self.motion:
            logger.info("MOTION EVENT TRIGGERED")
            db_obj = {
                "event_id": self.event_id,
                "type": "motion",
                "start_time": time,
                "notes": f"{motion}"
            }
            DBHandler.insert(table="classifier", data=db_obj, target=DBTarget.LOCAL, user="electric", handler=self.handler)
        self.motion = motion
        
    def update_trajectory(self, trajectory: Trajectory, time: float):
        # Trigger event
        if trajectory != self.trajectory:
            logger.info("TRAJECTORY EVENT TRIGGERED")
            db_obj = {
                "event_id": self.event_id,
                "type": "trajectory",
                "start_time": time,
                "notes": f"{trajectory}"
            }
            DBHandler.insert(table="classifier", data=db_obj, target=DBTarget.LOCAL, user="electric", handler=self.handler)
        self.trajectory = trajectory
        

    def check_motion(self, points: NDArray, window_size, acceleration_threshold_average: float = 1, deceleration_threshold_average: float = -1, acceleration_threshold_regression: float = 1, deceleration_threshold_regression: float = -1, mode = 2):
        """
        Updates the motion value based on points
        
        ARGS:
        points: array containing velocities, heading, and time
        acceleration_threshold_average: threshold to start an acceleration event using average acceleration
        deceleration_threshold_average: threshold to start a deceleration event using average acceleration
        acceleration_threshold_regression: slope to start an acceleration event using regression
        deceleration_threshold_regression: slope to start a deceleration event using regression
        mode: 0 = average method only, 1 = regression method only, 2 = either or or
        
        
        A
        0. Threshold: immobile if speed < t0
        1. Threshold: no event if speed < t1
        2. Start acceleration when avg of x1 last pts > t2
        3. Start deceleration when avg of x2 last pts < t3
        
        B
        0. Threshold: immobile if speed < t0
        1. Threshold: no event if speed < t1
        2. Linear regression of speed to time over last x3 pts
        3. Start acceleration if slope > t4
        4. Start deceleration if slope < t5
        """
    
        assert acceleration_threshold_average > 0
        assert deceleration_threshold_average < 0
        assert acceleration_threshold_regression > 0
        assert deceleration_threshold_regression < 0
        
        motion = self.motion
        
        average_velocity = (points[:, 0]).mean()
        
        # A ----------
        if mode == 0 or mode == 2:
            delta_velocities = np.diff(points[:, 0])
            delta_times = np.diff(points[:, 2])

            accelerations = delta_velocities / (delta_times / 1000)
            
            mean = accelerations.mean()
            
            # acceleration
            if mean > acceleration_threshold_average:
                motion = Motion.ACCELERATION
            # deceleration
            elif mean < deceleration_threshold_average:
                motion = Motion.DECELERATION
                
        # B --------- 
        elif mode == 1 or mode == 2:
            smoothed_velocities = np.polyfit(points[:, 2], points[:, 0], 1)
            # acceleration - ax + b where a > threshold
            if smoothed_velocities[0] > acceleration_threshold_regression:
                motion = Motion.ACCELERATION
            # deceleration - ax + b where a < threshold
            elif smoothed_velocities[0] < deceleration_threshold_regression:
                motion = Motion.DECELERATION
        
        self.update_motion(motion=motion, time=points[2][window_size / 2])
          
    def check_trajectory(self, points: NDArray, window_size, turning_threshold_average: float = 1, linear_threshold_average: float = 0.5, turning_threshold_regression: float = 1, linear_threshold_regression: float = 0.5, mode = 2):
        """
        Updates the trajectory value based on points
        
        ARGS:
        points: array containing velocities, heading, and time
        turning_threshold_average: threshold to start a turning event using average heading speed
        linear_threshold_average: threshold to start a linear event using average heading speed
        turning_threshold_regression: slope to start a turning event using regression
        linear_threshold_regression: threshold to start a linear event using regression
        mode: 0 = average method only, 1 = regression method only, 2 = either or or
        """
        assert turning_threshold_average > linear_threshold_average
        assert turning_threshold_regression > linear_threshold_regression
        assert turning_threshold_average > 0
        assert turning_threshold_regression > 0
        
        trajectory = self.trajectory
        
        average_velocity = (points[:, 0]).mean()
        
        # A ----------
        if mode == 0 or mode == 2:
            delta_heading = np.diff(points[:, 1])
            delta_times = np.diff(points[:, 2])

            speeds = delta_heading / (delta_times / 1000)
            
            mean = speeds.mean()
            
            max = speeds.max()
            
            # turn right
            if mean > turning_threshold_average:
                trajectory = Trajectory.TURN_RIGHT
            # turn left
            elif mean < -turning_threshold_average:
                trajectory = Trajectory.TURN_LEFT
            # go straight
            elif mean < linear_threshold_average and mean > linear_threshold_average:
                trajectory = Trajectory.LINEAR
                
        # B --------- 
        elif mode == 1 or mode == 2:
            smoothed_heading = np.polyfit(points[:, 2], points[:, 1], 1)
            if smoothed_heading[0] > turning_threshold_regression:
                trajectory = Trajectory.TURN_RIGHT
            elif smoothed_heading[0] < -turning_threshold_regression:
                trajectory = Trajectory.TURN_LEFT
            elif smoothed_heading[0] < linear_threshold_regression and smoothed_heading[0] > -linear_threshold_regression:
                trajectory = Trajectory.LINEAR
        
        self.update_trajectory(motion=trajectory, average_velocity=average_velocity, time=points[2][window_size / 2])
            
   
    def run_thread(self, handler: DBHandler, frequency: int, window_size: int):
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
            
            points  = np.array(handler.simple_select(f"SELECT d.gps_velocity, d.gps_heading, p.time FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id WHERE d.packet_id >= {self.start_packet} ORDER BY d.packet_id DESC LIMIT {window_size}", handler=handler, target=DBTarget.LOCAL))
            
            # Checks if at rest
            if math.abs(points[:, 0].mean()) < self.VELOCITY_THRESHOLD:
                self.motion = Motion.SLOW
                self.trajectory = Trajectory.SLOW
                sleep(1 / frequency)
                continue
            
            self.check_motion(points=points, window_size=window_size, mode=2)
            self.check_trajectory(points=points, window_size=window_size, mode=2)
        
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
        
        processor = GPSClassifierProcessor()
        handler = DBHandler()
        
        # Processing thread
        t1 = threading.Thread(target=processor.run_thread, args=(handler, 1, 50,))
        t1.start()
        
        mqtt.client.on_message = processor.on_message
        mqtt.subscribe("config/test")
        
        
# Goals

# Detect:
    # - accelerations
    # - turns
    
# Accelerations:
    # - Just like lap timer, select x latest points ✅
    # - Sliding window
    # - vcu_accel
    # - threshold
    # - Linear approximation
    # - Convert to 1d array of signed magnitude
    # - Check for a change greater than threshold
    
    
    
    # - Sliding window
    # - If turn / deceleration --> look for acceleration in a straight line
        # - Smooth y based on x in n = 1 to get y = Ax + B
        # - Flatten to 1D
        # - Smooth pos based on t in 1D to get pos = At + B
        # - If A > threshold > threshold: start acceleration
    # - If acceleration --> look for deceleration
    
    # - Turn
        # - Smooth y based on x in n = 2 to get y = Ax^2 + Bx + C
        # - Get curvature 
        # - If ∆ curvature > threshold: start turn
        # - If 
    