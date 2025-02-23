import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import pickle
import time
import logging
import datetime
import os
import psycopg
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
import gc
import shutil
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path
from tqdm import tqdm
from psycopg.types.json import Jsonb
from queue import Queue

import requests

sys.path.append(str(Path(__file__).parents[2]))

from analysis.sql_utils.db_handler import get_table_column_specs
from analysis.sql_utils.db_handler import DBHandler, DBTarget
from stack.ingest.mqtt_handler import MQTTHandler, MQTTTarget

class CSVToDB():

    def __init__(self, data_csv_folder, mqtt, db_handler = None, MQQT_target = MQTTTarget.LOCAL):
        self.db_handler = db_handler
        self.MQTT_target = MQQT_target
        self.mqtt = mqtt
        self.last_packet = 0
        try:
            self.data_csv_folder = sorted(list(Path.cwd().joinpath("csv_data", data_csv_folder).glob("*.csv")))
        except FileNotFoundError:
            logging.warning("NO FOLDER OF CSV FILES WERE SPECIFIED. ENSURE A FOLDER IS SELECTED OR DATA IS IN csv_data")
            self.data_csv_folder = sorted(list(Path.cwd().joinpath("csv_data").glob("*.csv")))

    def combine_all_csv(self):
        return pd.concat([pd.read_csv(self.data_csv_folder[i]) for i in range(len(self.data_csv_folder))], ignore_index=True)

    def event_seperator(self, threshold = 20):
        """"
        The class variable is a directory containing csv files from a certain drive day. The goal of this method is to 
        partition the folder into continous segments in which the car is running, outputting a list containing dataframes
        where each dataframe represents a near continous time period in which the car is running. 
        """
        csv_split = []
        event = [pd.read_csv(self.data_csv_folder[0])]
        df_current = pd.read_csv(self.data_csv_folder[0])
        
        if (len(self.data_csv_folder) == 1):
            event_storage = Path.cwd().joinpath("event_csv")
            df_current.to_csv(event_storage.joinpath("0.csv"))
            return

        for i in tqdm(range(len(self.data_csv_folder) - 1)):
            df_forw = pd.read_csv(self.data_csv_folder[i+1])

            last_dt_current = df_current.iloc[-1]
            dt_current = pd.to_datetime({"year" : [last_dt_current["Year"] + 2000], 
                "month" : [last_dt_current["Month"]], 
                "day" : [last_dt_current["Day"]], 
                "hour" : [last_dt_current["Hour"]], 
                "minute" : [last_dt_current["Minute"]], 
                "second" : [last_dt_current["Seconds"]], 
                "millisecond" : [last_dt_current["Milliseconds"]]}).astype(int) // 1000000 #gets into ms

            first_dt_forw = df_forw.iloc[0]
            dt_forw = pd.to_datetime({"year" : [first_dt_forw["Year"] + 2000], 
                "month" : [first_dt_forw["Month"]], 
                "day" : [first_dt_forw["Day"]], 
                "hour" : [first_dt_forw["Hour"]], 
                "minute" : [first_dt_forw["Minute"]], 
                "second" : [first_dt_forw["Seconds"]], 
                "millisecond" : [first_dt_forw["Milliseconds"]]}).astype(int) // 1000000 #gets into ms

            if (dt_forw[0] - dt_current[0] < threshold * 1000):
                differences = df_forw.Time - df_forw.Time.shift(fill_value=0)
                # df.time - df.time.shift(fill_value=0)
                df_forw["Time"][0] = df_current["Time"].iloc[-1] + ((dt_forw[0] - dt_current[0])//1000) #Find differing times
                df_forw["Time"] = df_forw["Time"].iloc[0] + differences.cumsum()
                df_current = df_forw
                event.append(df_forw)
            else:
                csv_split.append(pd.concat(event, ignore_index=True))
                event = [df_forw]
                df_current = df_forw
                if (i == len(self.data_csv_folder) - 2):
                    csv_split.append(pd.concat(event))

        time_arrays = [np.array(entry["Time"]) for entry in csv_split]
        time_diff = [np.diff(time_array) for time_array in time_arrays]
        delays = [np.where(diff >= threshold)[0] for diff in time_diff]
        
        #Find instances of car moving fast/high motor output. Keep a running mean /median and compare with the current value.
        #Incorporate some future and past values

        #TODO event separation using wheel speeds
        

        continous_event = []
        #Partition into continous event list
        for i, (df, delay_indices) in enumerate(zip(csv_split, delays)):
            start_idx = 0
            for delay_idx in delay_indices:
                continous_event.append(df.iloc[start_idx:delay_idx])  
                start_idx = delay_idx 
            continous_event.append(df.iloc[start_idx:])
        
        event_storage = Path.cwd().joinpath("event_csv")
        if not os.path.exists(event_storage): 
            os.makedirs(event_storage) 
        for i in range(len(continous_event)):
            continous_event[i].to_csv(event_storage.joinpath(f'{i}.csv'))

        del continous_event
        del df_current
        del df_forw

        gc.collect()

    def get_Tables(self):
        """
        Creates a dictionary based on get_table_column_specs to hold data to be added to the database
        """
        ent = get_table_column_specs()
        for i, sub_dict in ent.items():
            for j in sub_dict:
                sub_dict[j] = []
        return ent

        
    def enumerate_packet_id(self, data_csv):       
        """
        Enumerates the packet_id from the last known packet_id. Uses the csv with car data to determine amount of packet_id to add
        """
        try: 
            #last_packet    
            last_packet = max(DBHandler.simple_select("SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1", 
                                                      target=DBTarget.LOCAL, user='electric', handler=self.db_handler)[0][0], 
                                                      self.last_packet)
        except IndexError:
            last_packet = self.last_packet

        df = data_csv
        pack_id = list(range(last_packet + 1, last_packet+1+len(df.index)))
        self.last_packet = last_packet + len(df.index)
        return pack_id

    def dataConvert(self, df, table_desc):
        """
        Converts data to the csv to a format that can be added into the database
        """
        convert = {}
        #pg to csv

        pg_to_csv = {
            "time" : "Time",
            "torque_request": "Inverter Torque Request",
            "vcu_position": ["Vehicle Displacement X", "Vehicle Displacement Y", "Vehicle Displacement Z"],
            "vcu_velocity": ["Vehicle Velocity X", "Vehicle Velocity Y", "Vehicle Velocity Z"],
            "vcu_accel": ["Vehicle Acceleration X", "Vehicle Acceleration Y", "Vehicle Acceleration Z"],
            "gps": ["Latitude", "Longitude"],
            "gps_velocity": "Speed",
            "gps_heading": "Heading",
            "body1_accel": ["VCU Acceleration X", "VCU Acceleration Y", "VCU Acceleration Z"],
            "body2_accel": ["HVC Acceleration X", "HVC Acceleration Y", "HVC Acceleration Z"],
            "body3_accel": ["PDU Acceleration X", "PDU Acceleration Y", "PDU Acceleration Z"],
            "flw_accel": ["Front Left Acceleration X", "Front Left Acceleration Y", "Front Left Acceleration Z"],
            "frw_accel": ["Front Right Acceleration X", "Front Right Acceleration Y", "Front Right Acceleration Z"],
            "blw_accel": ["Back Left Acceleration X", "Back Left Acceleration Y", "Back Left Acceleration Z"],
            "brw_accel": ["Back Right Acceleration X", "Back Right Acceleration Y", "Back Right Acceleration Z"],
            "body1_gyro": ["VCU Gyro X", "VCU Gyro Y", "VCU Gyro Z"],
            "body2_gyro": ["HVC Gyro X", "HVC Gyro Y", "HVC Gyro Z"],
            "body3_gyro": ["PDU Gyro X", "PDU Gyro Y", "PDU Gyro Z"],
            "flw_speed": "Front Left Wheel Speed",
            "frw_speed": "Front Right Wheel Speed",
            "blw_speed": "Back Left Wheel Speed",
            "brw_speed": "Back Right Wheel Speed",
            "inverter_v": "Voltage",
            "inverter_c": "Current",
            "inverter_rpm": "RPM",
            "inverter_torque": "Actual Torque",
            "apps1_v": "APPS 1 Voltage",
            "apps2_v": "APPS 2 Voltage",
            "bse1_v": "BSE 1 Voltage",
            "bse2_v": "BSE 2 Voltage",
            "sus1_v": "Suspension 1 Voltage",
            "sus2_v": "Suspension 2 Voltage",
            "steer_v": "Steer Voltage",
            "hv_pack_v": "Pack Voltage Mean",
            "hv_tractive_v": "Voltage Input into DC",
            "hv_c": "Current Input into DC",
            "lv_v": "LV Voltage",
            "lv_c": "LV Current",
            "contactor_state": "Contactor Status",
            "avg_cell_v": "Cell Voltage Mean",
            "avg_cell_temp": "Cell Temps Mean",
            "hv_charge_state": "State of Charge",
            "lv_charge_state": "LV State of Charge",
            "cells_temp": ["Segment 1 Max", "Segment 1 Min", "Segment 2 Max", "Segment 2 Min", 
                        "Segment 3 Max", "Segment 3 Min", "Segment 4 Max", "Segment 4 Min"],
            "inverter_temp": "Inverter Temp",
            "motor_temp": "Motor Temp",
            "water_motor_temp": "Water Temp Motor",
            "water_inverter_temp": "Water Temp Inverter",
            "water_rad_temp": "Water Temp Radiator",
            "rad_fan_rpm": "Radiator Fan RPM Percentage",
            "flow_rate": "Volumetric Flow Rate"
        }
        packet_ids = self.enumerate_packet_id(df)
        for table in table_desc:
            convert[table] = {}
            for column, (dtype, ndim) in table_desc[table].items():
                if column not in {"time", "packet_id", "gps", } and column in pg_to_csv:
                    if (ndim):
                        convert[table][column] = df[pg_to_csv[column]].astype(dtype).to_numpy().tolist()
                        # if (table == "thermal"):
                        #     print (column, any(value > 32767 or value < -32768 for sublist in df[pg_to_csv[column]].astype(dtype).to_numpy().tolist() for value in sublist))
                    else:
                        convert[table][column] = df[pg_to_csv[column]].astype(dtype)
                        # if (table == "thermal"):
                        #     print (column, any(value > 32767 or value < -32768 for value in df[pg_to_csv[column]].astype(dtype)))
                elif (column == "time"):
                    df.Year += 2000
                    first_dt = df.iloc[0]
                    dt = pd.to_datetime({"year" : [first_dt["Year"]], 
                        "month" : [first_dt["Month"]], 
                        "day" : [first_dt["Day"]], 
                        "hour" : [first_dt["Hour"]], 
                        "minute" : [first_dt["Minute"]], 
                        "second" : [first_dt["Seconds"]], 
                        "millisecond" : [first_dt["Milliseconds"]]}).astype(int) // 1000000 #gets into ms
                    offset = df["Time"][0] * 1000 #get into ms
                    dt_list = ((dt[0] - offset) + (df["Time"] * 1000)).astype(int)
                    convert[table][column] = dt_list
                elif (column == "packet_id"):
                    convert[table][column] = packet_ids
                elif (column == "gps"):
                    convert[table][column] = np.column_stack((df["Latitude"], df["Longitude"])).tolist()
                else:
                    convert[table][column] = []

        return convert


    #Each iteration makes a new connection to the database and sends a singular row at a time
    def insert_row_from_csv(self, df, num_rows : int):
        """
        Adds data into the database. First adds packet table, then subsequent table using DBHandler insert function. Each iteration
        only inputs a singular row to the database, making this program the least efficient
        """
        data = self.dataConvert(df)
        packets = data["packet"]
        for i in tqdm(range(num_rows)):
            row_dict = {j : packets[j][i] for j in packets if (len(packets[j] != 0))}
            DBHandler.insert(table="packet", data=row_dict, user = "electric", handler = self.db_handler)
            logging.info(row_dict)

        for i in tqdm(data.keys()):
            if (i not in {"packet", "event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"}):
                for j in range(num_rows):
                    row_dict = {k : data[k][j] for k in data[i] if (len(data[i][k]) != 0)}
                    DBHandler.insert(table = i, data = row_dict, user="electric", handler = self.db_handler)

    def insert_multi_row_from_csv(self, df, amt = 2000):
        """
        Inserts data into the database in larger batches determined by the given amt value. 
        """
        # Setup data within method--------------------------------------------------------------------------------
        data = self.dataConvert(df, table_desc=table_desc)
        packets = data["packet"]
        for j in tqdm(range(0, len(df.index), amt)):
            pack_list = []
            high = min(j + amt, len(df.index))
            pack_list = [{j : packets[j][i] for j in packets if (len(packets[j]) != 0)} for i in range(j, high, 1)]
            DBHandler.insert_multi_rows(table="packet", data = pack_list, user="electric", handler = self.db_handler)

            for i, values in data.items():
                row_list = []
                if (i not in ["packet", "event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"]):
                    row_list = [{k : values[k][j] for k in values if (len(values[k]) != 0)} for j in range(j, high, 1)]
                    DBHandler.insert_multi_rows(table = i, data = row_list, user="electric", handler = self.db_handler)

    def stream_data(self, df):
        for chunk in (pd.read_csv(df, chunksize=2000)):
            yield chunk.reset_index(drop = True)

    def event_playback(self, file_path, table_desc, time_adjustment = True):
        """
        Publishes to database based on time delays from the csv
        """
        def publish_row():
            """
            Takes data from a csv and sends data in rows to mqtt for event playback. Data is formatted as a dictionary and published
            to mqtt through small batches of rows
            """
            
            started = False
            
            while not done or not chunk_queue.empty():

                if (not chunk_queue.empty()):
                    differences, row_dict_list = chunk_queue.get()
                    chunk_length = len(differences)
                    
                    if not started:
                        try:
                            self.start_timer(row_dict_list.get("packet")[0]['time'])
                            started = True
                        except Exception as e:
                            print(e)

                    for i in tqdm(range(chunk_length)):
                        time.sleep(float(float(differences[i])/ 1000))
                        if (i % 10 == 0):
                            for table in ['packet', 'dynamics', 'controls', 'pack', 'diagnostics', 'thermal']: #Through the different tables
                                end_index = min(i + 10, chunk_length)  # Ensure we don't exceed the length
                                batch_data = row_dict_list.get(table)[i:end_index]
                                self.mqtt.publish(f'data/{table}', pickle.dumps(batch_data), qos=0)
                else:
                    time.sleep(0.1)
                    
            if started:
                self.stop_timer()

        def setup_rows(df, table_desc, time_adjustment):
            """"
            Formats the rows in the form of dictionaries to be sent into database
            """
            data = self.dataConvert(df, table_desc=table_desc)
            differences = []
            times = np.array(data["packet"]["time"])
            differences = np.insert(np.diff(times), 0, 0)
            if (time_adjustment):
                data["packet"]["time"] = current_time[0] + np.cumsum(differences)
                current_time[0] =  current_time[0] + np.sum(differences)

            row_dict_list = {}
            for i, values in data.items():
                row_list = []
                if (i not in {"event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"}):
                    row_list = [DBHandler.get_insert_values(table = i, data={k : values[k][j] for k in values if (len(values[k]) != 0)},
                                table_desc=table_desc[i]) for j in range(len(df.index))]
                    row_dict_list[i] = row_list
            return differences, row_dict_list
        
        with ThreadPoolExecutor(max_workers=1) as setup_executor:
            with ThreadPoolExecutor(max_workers=1) as publish_executor:
                setup_future = None
                chunk_queue = Queue()
                done = False
                current_time = [int(datetime.datetime.timestamp(datetime.datetime.now())*1000)]
                try:
                    publish_future = publish_executor.submit(publish_row)
                    for df in self.stream_data(file_path):
                        if setup_future:
                            setup_future.result()
                        setup_future = setup_executor.submit(setup_rows, df, table_desc, time_adjustment)

                        differences, row_dict_list = setup_future.result()
                        chunk_queue.put((differences, row_dict_list))
                    done = True
                    if setup_future:
                        setup_future.result()

                    publish_future.result() 
                except KeyboardInterrupt:
                    setup_executor.shutdown(False)
                    publish_executor.shutdown(False)

    def handle_event_start(self):
        # ---- START EVENT ----
        try:
            event_id = (DBHandler.simple_select('SELECT event_id FROM event WHERE status = 1 ORDER BY event_id DESC LIMIT 1', handler=self.db_handler)[0][0])
            if event_id == -1: raise Exception("No event is currently running")
        # Creating a new event
        except Exception as e:
            sample_drive_day = {'power_limit': '', 'conditions': ''}
            sample_event = {'driver_id': '0', 'location_id': '0', 'event_type': '0', 'car_id': '1', 'car_weight': '', 'tow_angle': '', 'camber': '', 'ride_height': '', 'ackerman_adjustment': '', 'power_limit': '', 'shock_dampening': '', 'torque_limit': '', 'frw_pressure': '', 'flw_pressure': '', 'brw_pressure': '', 'blw_pressure': '', 'day_id': '1'}
            
            day_id = DBHandler.insert(table='drive_day', target=os.getenv('SERVER_TARGET', DBTarget.LOCAL), user='electric', data=sample_drive_day, returning='day_id', handler=self.db_handler)
            response = requests.post("http://localhost:5000/create_event/", data=sample_event)
            
            with MQTTHandler('flask_app') as mqtt:
                mqtt.publish('config/page_sync', "running_event_page")
                
        #! CAN CHANGE
        config = {"event_id": 1, "gate": ((30.3870, -97.7253), (30.3869, -97.7252)), "status": 0, "start_packet": 0}
        print(config)
        self.mqtt.publish(f'config/test', json.dumps(config))
                
    def start_timer(self, start_time: int):
        config = {
            "timerRunning": True,
            "timerEventTime": start_time,
            "timerInternalTime": 0,
        }
        print("STARTED TIMER AT ", start_time)
        print(config)
        self.mqtt.publish('config/event_sync', json.dumps(config, indent=4))
        
    def stop_timer(self):
        config = {
            "timerRunning": False,
            "useInternalTime": True
        }
        print(config)
        self.mqtt.publish('config/event_sync', json.dumps(config, indent=4))
        
        
if __name__ == '__main__':

    logging.basicConfig(level=logging.CRITICAL)
    # Playback testing ---------------------------------------------------------------------------------------------
    with DBHandler(unsafe=True, target=DBTarget.LOCAL) as db:
        with MQTTHandler(name ='event_playback_test', target = MQTTTarget.LOCAL, db_handler=db) as mqtt:
            db.connect(target = DBTarget.LOCAL, user = 'electric')
            
            dataSender = CSVToDB("2024_10_13__001_AutoXCompDay", db_handler=db, mqtt=mqtt)
            dataSender.handle_event_start()
            
            
            table_desc = get_table_column_specs()
            ## Event playback functionarlity code TODO---------------------------------------------------------------------------------
            #dataSender.event_seperator(threshold=5) #Saves list to harddrive
            mqtt.connect()
            #Where the csv is stored
            dataSender.event_playback(Path.cwd().joinpath("csv_data/gps_classifier_tests").joinpath("Log__2024_10_11__05_50_47.csv"), table_desc=table_desc)
            
            #dataSender.dataConvert(pd.read_csv(Path.cwd().joinpath("event_csv").joinpath("8.csv")), table_desc=table_desc)
            #shutil.rmtree(Path.cwd().joinpath("event_csv"))
       