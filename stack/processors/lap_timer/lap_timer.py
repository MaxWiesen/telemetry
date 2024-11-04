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
import requests

if os.getenv('IN_DOCKER'):
    from db_handler import DBHandler, DBTarget, get_table_column_specs    # Cheesed import statement using bind mount
    from mqtt_handler import MQTTHandler
else:
    from analysis.sql_utils.db_handler import DBHandler, DBTarget, get_table_column_specs
    from stack.ingest.mqtt_handler import MQTTHandler

class LapTimerProcessor:
    def __init__(self, db_handler: DBHandler=None):
        self.handler = db_handler if db_handler else DBHandler()
        self.event_id: int = None
        self.gate: tuple[tuple[float], tuple[float]]  = None
        self.status: int = None
        
        self.start_packet: int = 0

    def check_alive(self) -> None:
        logging.info(self.handler.simple_select('''SELECT event_id FROM event WHERE status = 1''', handler=self.handler))

    def sliding_window(self, f, query: str, window_size: int, **kwargs) -> None:
        """
            Args:
                f: function to execute with the result of the query
                query: SQL query to run
                window_size: Maximum # of packets to be collected
        """
        
        
        df = self.handler.simple_select(query, handler=self.handler, return_df=True)
        f(df, **kwargs)
        
        
        
        
        

    def _track_lap(self, gate: tuple[tuple[float, float], tuple[float, float]], points: list) -> float | None:
        """
        Checks if a circuit loop has happened after a given packet
        Args:
            last_packet: checking after this value
            gate: human-measured gate that represents the starting line
        """
        
        
        # points: list[tuple[str, int]] = handler.simple_select(f"SELECT d.gps, p.time FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id WHERE d.packet_id >= {last_packet} ORDER BY d.packet_id ASC LIMIT 500", handler=handler, target=DBTarget.LOCAL)
        
    
        for i in range(len(points) - 1):
            if(self._is_intersection(gate, [points[i][0], points[i + 1][0]])):
                return round((points[i][1] + points[i + 1][1]) / 2)
        
    def _is_intersection(self, line1: tuple[tuple[float, float], tuple[float, float]], line2: tuple[tuple[float, float], tuple[float, float]]) -> bool:
        """
        Check if a line intersects with another line segment 
        """

        # Calculate the denominator of the intersection formula
        denominator = (line1[0][1] - line1[1][1]) * (line2[0][0] - line2[1][0]) - (line1[0][0] - line1[1][0]) * (line2[0][1] - line2[1][1])

        # If the denominator is zero, the lines are parallel
        if denominator == 0:
            return False  # Parallel lines

        # Calculate t and u
        t = ((line1[0][1] - line2[0][1]) * (line2[0][0] - line2[1][0]) - (line1[0][0] - line2[0][0]) * (line2[0][1] - line2[1][1])) / denominator
        u = ((line1[0][1] - line2[0][1]) * (line1[0][0] - line1[1][0]) - (line1[0][0] - line2[0][0]) * (line1[0][1] - line1[1][1])) / denominator

        # Check if t and u are between 0 and 1 (i.e., the intersection occurs within the segments)
        return 0 <= t <= 1 and 0 <= u <= 1
    
    def _is_valid(self, time:int, handler: DBHandler, delta: int):
        if self.event_id == None:
            return False
        query = handler.simple_select(f"SELECT start_time FROM classifier c WHERE event_id = {self.event_id} ORDER BY start_time DESC LIMIT 1")
        if not query or len(query) == 0:
            return True
        last_lap: int = query[0][0]
        return time - last_lap > delta
        
    
    def _record_time(self, time: int, handler: DBHandler):
        if self.event_id == None:
            return
        
        db_obj = {
            "event_id": self.event_id,
            "type": "lap",
            "start_time": time
        }
        
        logging.debug("DB OBJ")
        logging.debug(db_obj)
        
        # Start time
        if self.status != 1:
            handler.set_event_status(event_id=self.event_id, status=1, user='electric', start_time=time, returning='day_id')
        
        handler.insert(table="classifier", data=db_obj, target=DBTarget.LOCAL, user="electric")
        requests.post("http://" + os.environ["HOST_IP"] + ":5000/new_lap", data={"time": time})
        logging.info(f"Successfully recorded time {time}")
    
    # def run_thread(self, handler):
    #     """Grabs all the points and does sliding window on here"""
    #     while True:
    #         if not self.event_id or not self.gate:
    #             logging.info("No Event ID or Gate...")
    #             sleep(5)
    #             continue
    #         else:
    #             logging.debug(f"Event ID: {self.event_id} | Gate: {self.gate}")
    #         query = DBHandler.simple_select("SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1", target=DBTarget.LOCAL, handler=handler)
    #         sleep(5)
    #         # No Packet
    #         last_packet = 0 if query == None or len(query) == 0 else query[0][0]
    #         # Get Time of intersect
    #         loop = self._track_lap(last_packet=last_packet, gate=self.gate, handler=handler)
    #         if loop:
    #             # Is timestamp valid? 
    #             if self._is_valid(time=loop, handler=handler, delta=10):
    #                 # Add time to classifier
    #                 logging.info(f"Lap Time is Valid")
    #                 self._record_time(time=loop, handler=handler)
    #             else:
    #                 logging.warning(f"Lap Time is Not Valid")
    #         else:
    #             logging.info("No lap detected")
    
    
    def _latlon_to_ecef(self, lat: float, lon: float) -> tuple[float, float, float]:
        # Constants
        R = 6371000  # Earth radius in meters

        # Convert latitude and longitude to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        # Convert to Cartesian coordinates
        x = R * math.cos(lat_rad) * math.cos(lon_rad)
        y = R * math.cos(lat_rad) * math.sin(lon_rad)
        z = R * math.sin(lat_rad)

        return x, y, z

    def _ecef_to_latlon(self, x: float, y: float, z: float) -> tuple[float, float]:
        # Constants
        R = 6371000  # Earth radius in meters

        # Convert back to latitude and longitude
        lat = math.degrees(math.asin(z / R))
        lon = math.degrees(math.atan2(y, x))

        return lat, lon

    def _smooth_points(self, points: list[tuple[tuple[float, float], int]], order: int) -> None:
        if order < 1 or len(points) <= order:
            # If the order is less than 1 or not enough points, do nothing
            return

        # Extract timestamps and convert latitude, longitude to ECEF coordinates
        timestamps = [point[1] for point in points]
        ecef_coords = [self._latlon_to_ecef(point[0][0], point[0][1]) for point in points]
        x_coords, y_coords, z_coords = zip(*ecef_coords)

        # Fit an n-th order polynomial to each of the Cartesian coordinates
        poly_x = np.polyfit(timestamps, x_coords, order)
        poly_y = np.polyfit(timestamps, y_coords, order)
        poly_z = np.polyfit(timestamps, z_coords, order)

        # Evaluate the polynomial at each timestamp to get smoothed Cartesian coordinates
        smoothed_points = []
        for t in timestamps:
            smoothed_x = np.polyval(poly_x, t)
            smoothed_y = np.polyval(poly_y, t)
            smoothed_z = np.polyval(poly_z, t)
            # Convert smoothed Cartesian coordinates back to latitude and longitude
            smoothed_lat, smoothed_lon = self._ecef_to_latlon(smoothed_x, smoothed_y, smoothed_z)
            # Append smoothed point with the original timestamp
            smoothed_points.append(((smoothed_lat, smoothed_lon), t))

        # Modify the original list in place
        points[:] = smoothed_points

    def _upload_gates_to_db(self, gates: tuple[tuple[float, float], tuple[float, float]]):
        db_obj = {
            "event_id": self.event_id,
            "type": "gate",
            "notes": f"{gates[0][0]}_{gates[0][1]}_{gates[1][0]}_{gates[1][1]}",
            "start_time": time.time() * 1000 #! Might need to change this?
        }
        self.handler.insert(table="classifier", data=db_obj, target=DBTarget.LOCAL, user="electric")
        
        logging.info("Published gates to classifier", db_obj)
   
    def run_thread(self, handler, frequency: int, window_size: int):
        """Sliding Window"""
        while True:
            # Event not properly set
            if not self.event_id or not self.gate:
                logging.info("No Event ID or Gate...")
                sleep(1 / frequency)
                continue
            else:
                logging.debug(f"Event ID: {self.event_id} | Gate: {self.gate} | Status: {self.status}")
                
            points: list[tuple[str, int]] = handler.simple_select(f"SELECT d.gps, p.time FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id WHERE d.packet_id >= {self.start_packet} ORDER BY d.packet_id DESC LIMIT {window_size}", handler=handler, target=DBTarget.LOCAL)
            # print(f"SELECT d.gps, p.time FROM dynamics d JOIN packet p ON p.packet_id = d.packet_id WHERE d.packet_id >= {self.start_packet} ORDER BY d.packet_id DESC LIMIT {window_size}")

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
            
            # Parse points
            df = pd.DataFrame(points, columns=['gps_str', 'timestamp'])
            df['parsed_coordinates'] = df['gps_str'].apply(lambda gps_str: tuple(map(float, gps_str[1:-1].split(','))))
            points: list[tuple[tuple[float, float], int]] = list(zip(df['parsed_coordinates'], df['timestamp']))
            
            # Smooth points
            self._smooth_points(points=points, order=2)
            
            lap_time = self._track_lap(gate=self.gate, points=points)
            # Get Time of intersect
            if lap_time:
                # Is timestamp valid? 
                if self._is_valid(time=lap_time, handler=handler, delta=5000):
                    # Add time to classifier
                    logging.info(f"Lap Time is Valid")
                    self._record_time(time=lap_time, handler=handler)
                else:
                    logging.warning(f"Lap Time is Not Valid")
            else:
                logging.info("No lap detected")
            
            sleep(1 / frequency)
        
        
    def on_message(self, client: mqtt_client.Client, userdata, msg):
        try:
            logging.info(f"MESSAGE HAS BEEN RECEIVED AT TOPIC {msg.topic}")
            if msg.topic == 'config/test':
                data = json.loads(msg.payload.decode())
                # Modify object variables
                self.event_id = data['event_id']
                self.status = data['status']
                if self.gate != data['gate']:
                    self._upload_gates_to_db(gates=data['gate'])
                self.gate = data['gate']
                if self.start_packet < data['start_packet']:
                    self.start_packet = data['start_packet']
        except json.JSONDecodeError:
            self.event_id = None
            self.gate = None
            self.status = None
            self.start_packet = None
    

        
def run_processor():
    with MQTTHandler(name="terence_dev") as mqtt:
        
        processor = LapTimerProcessor()
        handler = DBHandler()
        
        # Processing thread
        t1 = threading.Thread(target=processor.run_thread, args=(handler, 1, 50,))
        t1.start()
        
        mqtt.client.on_message = processor.on_message
        mqtt.subscribe("config/test")