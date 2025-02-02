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
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from tqdm import tqdm
from psycopg.types.json import Jsonb

sys.path.append(str(Path(__file__).parents[2]))

from analysis.sql_utils.db_handler import get_table_column_specs
from analysis.sql_utils.db_handler import DBHandler, DBTarget
from stack.ingest.mqtt_handler import MQTTHandler, MQTTTarget

class CSVToDB():

    def __init__(self, data_csv_folder, mqtt, db_handler = None, MQQT_target = MQTTTarget.LOCAL):
        self.db_handler = db_handler
        self.MQTT_target = MQQT_target
        self.mqtt = mqtt
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
        for i in tqdm(range(len(self.data_csv_folder) - 1)):
            #df_current = pd.read_csv(self.data_csv_folder[csv_path])
            df_forw = pd.read_csv(self.data_csv_folder[i+1])

            last_dt_current = df_current.iloc[-1]
            #df_current["Year"] = df_current["Year"] + 2000
            dt_current = pd.to_datetime({"year" : [last_dt_current["Year"] + 2000], 
                "month" : [last_dt_current["Month"]], 
                "day" : [last_dt_current["Day"]], 
                "hour" : [last_dt_current["Hour"]], 
                "minute" : [last_dt_current["Minute"]], 
                "second" : [last_dt_current["Seconds"]], 
                "millisecond" : [last_dt_current["Milliseconds"]]}).astype(int) // 1000000 #gets into ms

            #df_forw["Year"] = df_forw["Year"] + 2000
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
        
        # time_diff = [[csv_split[i]["Time"][j] - csv_split[i]["Time"][j-1] for j in range(1, len(csv_split[i]))] for i in range(len(csv_split))]
        # delays = [[j for j in range(len(time_diff[i])) if time_diff[i][j] >= threshold] for i in range(len(time_diff))]

        time_arrays = [np.array(entry["Time"]) for entry in csv_split]
        time_diff = [np.diff(time_array) for time_array in time_arrays]
        delays = [np.where(diff >= threshold)[0] for diff in time_diff]
        
        #Find instances of car moving fast/high motor output. Keep a running mean /median and compare with the current value.
        #Incorporate some future and past values

        #TODO event separation using wheel speeds
        # def rolling_window(a, window):
        #     shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
        #     strides = a.strides + (a.strides[-1],)
        #     return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)
        # grad_thresh = 0.5
        # for i in tqdm(range(len(csv_split))):
        #     flw_speed = csv_split[i]["Front Left Wheel Speed"].rolling(10, min_periods = 1).mean() #Smoothing
        #     frw_speed = csv_split[i]["Front Right Wheel Speed"].rolling(10, min_periods = 1).mean()
        #     blw_speed = csv_split[i]["Back Left Wheel Speed"].rolling(10, min_periods = 1).mean()
        #     brw_speed = csv_split[i]["Back Right Wheel Speed"].rolling(10, min_periods = 1).mean()
        #     time = csv_split[i]["Time"]

        #     grad_flw = pd.Series(np.gradient(np.gradient(flw_speed, time), time)).rolling(20, min_periods = 1).std()
        #     grad_frw = pd.Series(np.gradient(np.gradient(frw_speed, time), time)).rolling(20, min_periods = 1).std()            grad_blw = (np.gradient(np.gradient(blw_speed, time), time), 20)
        #     grad_blw = pd.Series(np.gradient(np.gradient(blw_speed, time), time)).rolling(20, min_periods = 1).std()
        #     grad_brw = pd.Series(np.gradient(np.gradient(brw_speed, time), time)).rolling(20, min_periods = 1).std()

        #     length = len(flw_speed) if (len(flw_speed) == len(dflw_dt)) else 0
        #     print (len(grad_flw))
        #     print (len(flw_speed))

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
            last_packet = DBHandler.simple_select("SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1", target=DBTarget.LOCAL, user='electric', handler=self.db_handler)[0][0]
        except IndexError:
            last_packet = 0

        df = data_csv
        pack_id = list(range(last_packet + 1, last_packet+1+len(df.index)))
        return pack_id

    def dataConvert(self, df, table_desc):
        """
        Converts data to the csv to a format that can be added into the database
        """
        items = [j for i in table_desc for j in table_desc[i]]
        convert = {}
        for i in items:
            match i:

                #This is data that input by the user and not recorded by the car. These values would not be embedded in the csv file upload file
                
                    # case "day_id":
                    #     logging.info("day_id added")
                    # case "date":
                    #     logging.info("date added")
                    # case "power_limit":
                    #     logging.info("power_limit added")
                    # case "conditions":
                    #     logging.info("conditions added")
                    # case "event_id":
                    #     logging.info("event_id added")
                    # case "status":
                    #     logging.info("status added")
                    # case "creation_time":
                    #     logging.info("creation_time added")
                    # case "start_time":
                    #     logging.info("start_time added")
                    # case "end_time":
                    #     logging.info("end_time added")
                    # case "packet_start":
                    #     logging.info("packet start added")
                    # case "packet_end":
                    #     logging.info("packet_end added")
                    # case "car_id":
                    #     logging.info("car_id added")
                    # case "driver_id":
                    #     logging.info("driver_id added")
                    # case "location_id":
                    #     logging.info("location_id added")
                    # case "event_type":
                    #     logging.info("event_type added")
                    # case "event_index":
                    #     logging.info("event_index added")
                    # case "car_weight":
                    #     logging.info("car_weight added")
                    # case "tow_angle":
                    #     logging.info("tow_angle added")
                    # case "camber":
                    #     logging.info("camber added")
                    # case "ride_height":
                    #     logging.info("ride_height added")
                    # case "ackerman_adjustment":
                    #     logging.info("ackerman_adjustment added")
                    # case "shock_dampening":
                    #     logging.info("shock_dampening added")
                    # case "torque_limit":
                    #     logging.info("torque_limit added")
                    # case "frw_pressure":
                    #     logging.info("frw_pressure added")
                    # case "flw_pressure":
                    #     logging.info("flw_pressure added")
                    # case "brw_pressure":
                    #     logging.info("brw_pressure added")
                    # case "blw_pressure":
                    #     logging.info("blw_pressure added")
                    # case "front_wing_on":
                    #     logging.info("front_wing_on added")
                    # case "rear_wing_on":
                    #     logging.info("rear_wing_on added")
                    # case "regen_on":
                    #     logging.info("regen_on added")
                    # case "undertray_on":
                    #     logging.info("undertray_on added")
                    # case "type":
                    #     logging.info("type added")
                    # case "notes":
                    #     logging.info("notes added")

                #Covered by packet enumeration, can add in with rest of values later if the entries are all of the same length
                # case "packet_id":
                #     logging.info(i + ": added")

                #These are sensor readings found in the CSV
            
                case "time":
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
                    
                    convert[i] = dt_list
                    
                    logging.info(i + ": added")
                case "torque_request":
                    convert[i] = df["Inverter Torque Request"]
                    logging.info(i + ": added")
                case "vcu_position":
                    convert[i] =  df[["Vehicle Displacement X", "Vehicle Displacement Y", "Vehicle Displacement Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "vcu_velocity":
                    convert[i] = df[["Vehicle Velocity X", "Vehicle Velocity Y", "Vehicle Velocity Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "vcu_accel":
                    convert[i] = df[["Vehicle Acceleration X", "Vehicle Acceleration Y", "Vehicle Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "gps":
                    convert[i] = np.column_stack((df["Longitude"], df["Latitude"])).tolist()
                    logging.info(i + ": added")
                case "gps_velocity":
                    df["Speed"] = df["Speed"].astype("float32")
                    convert[i] = df["Speed"]
                    logging.info(i + ": added")
                case "gps_heading":
                    df["Heading"] = df["Heading"].astype("float32")
                    convert[i] = df["Heading"]
                    logging.info(i + ": added")
                case "body1_accel":
                    convert[i] = df[["VCU Acceleration X", "VCU Acceleration Y", "VCU Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "body2_accel":
                    convert[i] = df[["HVC Acceleration X", "HVC Acceleration Y", "HVC Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "body3_accel":
                    convert[i] = df[["PDU Acceleration X", "PDU Acceleration Y", "PDU Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "flw_accel":
                    convert[i] = df[["Front Left Acceleration X", "Front Left Acceleration Y", "Front Left Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "frw_accel":
                    convert[i] = df[["Front Right Acceleration X", "Front Right Acceleration Y", "Front Right Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "blw_accel":
                    convert[i] = df[["Back Left Acceleration X", "Back Left Acceleration Y", "Back Left Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "brw_accel":
                    convert[i] = df[["Back Right Acceleration X", "Back Right Acceleration Y", "Back Right Acceleration Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "body1_gyro":
                    convert[i] = df[["VCU Gyro X", "VCU Gyro Y", "VCU Gyro Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "body2_gyro":
                    convert[i] = df[["HVC Gyro X", "HVC Gyro Y", "HVC Gyro Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "body3_gyro":
                    convert[i] = df[["PDU Gyro X", "PDU Gyro Y", "PDU Gyro Z"]].to_numpy().tolist()
                    logging.info(i + ": added")
                case "flw_speed":
                    convert[i] = df["Front Left Wheel Speed"]
                    logging.info(i + ": added")
                case "frw_speed":
                    convert[i] = df["Front Right Wheel Speed"]
                    logging.info(i + ": added")
                case "blw_speed":
                    convert[i] = df["Back Left Wheel Speed"]
                    logging.info(i + ": added")
                case "brw_speed":
                    convert[i] = df["Back Right Wheel Speed"]
                    logging.info(i + ": added")
                case "inverter_v":
                    convert[i] = df["Voltage"]
                    logging.info(i + ": added")
                case "inverter_c":
                    convert[i] = df["Current"]
                    logging.info(i + ": added")
                case "inverter_rpm":
                    convert[i] = df["RPM"].astype("int16")
                    logging.info(i + ": added")
                case "inverter_torque":
                    logging.info(i + ": added")
                    convert[i] = df["Actual Torque"]
                #Skip
                case "vcu_flags":
                    logging.info(i + ": added")
                case "vcu_flags_json":
                    logging.info(i + ": added")
                case "apps1_v":
                    convert[i] = df["APPS 1 Voltage"]
                    logging.info(i + ": added")
                case "apps2_v":
                    convert[i] = df["APPS 2 Voltage"]
                    logging.info(i + ": added")
                case "bse1_v":
                    convert[i] = df["BSE 1 Voltage"]
                    logging.info(i + ": added")
                case "bse2_v":
                    convert[i] = df["BSE 2 Voltage"]
                    logging.info(i + ": added")
                case "sus1_v":
                    convert[i] = df["Suspension 1 Voltage"]
                    logging.info(i + ": added")
                case "sus2_v":
                    convert[i] = df["Suspension 2 Voltage"]
                    logging.info(i + ": added")
                case "steer_v":
                    convert[i] = df["Steer Voltage"]
                    logging.info(i + ": added")
                case "hv_pack_v":
                    convert[i] = df["Pack Voltage Mean"]
                    logging.info(i + ": added")
                case "hv_tractive_v":
                    convert[i] = df["Voltage Input into DC"]
                    logging.info(i + ": added")
                case "hv_c":
                    convert[i] = df["Current Input into DC"]
                    logging.info(i + ": added")
                case "lv_v":
                    convert[i] = df["LV Voltage"]
                    logging.info(i + ": added")
                case "lv_c":
                    convert[i] = df["LV Current"]
                    logging.info(i + ": added")
                case "contactor_state":
                    convert[i] = df["Contactor Status"].astype("int16")
                    logging.info(i + ": added")
                case "avg_cell_v":
                    convert[i] = df["Cell Voltage Mean"]
                    logging.info(i + ": added")
                case "avg_cell_temp":
                    convert[i] = df["Cell Temps Mean"]
                    logging.info(i + ": added")
                #skip for now
                case "current_errors":
                    logging.info(i + ": not included")
                case "current_errors_json":
                    logging.info(i + ": not included")
                case "latching_faults":
                    logging.info(i + ": not included")
                case "latching_faults_json":
                    logging.info(i + ": not included")
                #resume
                #Using the mean with new data
                case "cells_v":
                    logging.info(i + ": added")
                
                case "hv_charge_state":
                    convert[i] = df["State of Charge"]
                    logging.info(i + ": added")
                case "lv_charge_state":
                    convert[i] = df["LV State of Charge"]
                    logging.info(i + ": added")
                #Update with new data
                case "cells_temp":
                    try:
                        convert[i] = df[["Segment 1 Max", "Segment 1 Min", "Segment 2 Max", 
                                                "Segment 2 Min", "Segment 3 Max", "Segment 3 Min", 
                                                "Segment 4 Max", "Segment 4 Min"]].to_numpy(dtype = np.int16).tolist()
                        logging.info(i + ": added")
                    except KeyError:
                        logging.info(i + ": not included")
                case "ambient_temp":
                    logging.info(i + ": not included")
                #Resume
                case "inverter_temp":
                    convert[i] = df["Inverter Temp"].astype("int16")
                    logging.info(i + ": added")
                case "motor_temp":
                    convert[i] = df["Motor Temp"].astype("int16")
                    logging.info(i + ": added")
                case "water_motor_temp":
                    convert[i] = df["Water Temp Motor"].astype("int16")
                    logging.info(i + ": added")
                case "water_inverter_temp":
                    convert[i] = df["Water Temp Inverter"].astype("int16")
                    logging.info(i + ": added")
                case "water_rad_temp":
                    convert[i] = df["Water Temp Radiator"].astype("int16")
                    logging.info(i + ": added")
                case "rad_fan_set":
                    logging.info(i + ": added")
                case "rad_fan_rpm":
                    convert[i] = df["Radiator Fan RPM Percentage"].astype("int16")
                    logging.info(i + ": added")
                case "batt_fan_set":
                    logging.info(i + ": not included")
                case "batt_fan_rpm":
                    logging.info(i + ": not included")
                case "flow_rate":
                    convert[i] = df["Volumetric Flow Rate"].astype("int16")
                    logging.info(i + ": added")
        convert["packet_id"] = self.enumerate_packet_id(df)

        fill = self.get_Tables()
        #loop through the different tables
        for i in fill:
            #Loop through the column names in each table
            for j in fill[i]:
                for k in convert:
                    if (k == j):
                        #Go to each table, find the columns to modify, insert new data
                        fill[i][k] = convert[k]
                    elif (k == "time" and j == "\"time\""):
                        fill[i][j] = convert[k]
        return fill

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

    def insert_multi_row_from_csv(self, chunk_length, row_dict_list, amt = 2000):
        """
        Inserts data into the database in larger batches determined by the given amt value. 
        """
        # Setup data within method--------------------------------------------------------------------------------
        # data = self.dataConvert(df, table_desc=table_desc)
        # packets = data["packet"]
        # for j in tqdm(range(0, len(df.index), amt)):
        #     pack_list = []
        #     high = min(j + amt, len(df.index))
        #     pack_list = [{j : packets[j][i] for j in packets if (len(packets[j]) != 0)} for i in range(j, high, 1)]
        #     DBHandler.insert_multi_rows(table="packet", data = pack_list, user="electric", handler = self.db_handler)

        #     for i, values in data.items():
        #         row_list = []
        #         if (i not in ["packet", "event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"]):
        #             row_list = [{k : values[k][j] for k in values if (len(values[k]) != 0)} for j in range(j, high, 1)]
        #             DBHandler.insert_multi_rows(table = i, data = row_list, user="electric", handler = self.db_handler)

        # Setup rows prior to batch sending------------------------------------------------------------------------------------
        for i in range(0, chunk_length, amt):
            min_index = min(chunk_length, i + amt)
            for table in ['packet', 'dynamics', 'controls', 'pack', 'diagnostics', 'thermal']:
                DBHandler.insert_multi_rows(table = table, data = row_dict_list[table][i : min_index], user = 'electric', handler = self.db_handler)

    def setup_rows(self, df, table_desc, time_adjustment = True):
        data = self.dataConvert(df, table_desc=table_desc)
        differences = []
        first_new_time = int(datetime.datetime.timestamp(datetime.datetime.now())*1000)
        times = np.array(data["packet"]["time"])
        differences = np.insert(np.diff(times), 0, 0)
        if (time_adjustment):
            data["packet"]["time"] = first_new_time + np.cumsum(differences)

        row_dict_list = {}
        for i, values in data.items():
            row_list = []
            if (i not in {"event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"}):
                row_list = [DBHandler.get_insert_values(table = i, data={k : values[k][j] for k in values if (len(values[k]) != 0)},
                            table_desc=table_desc[i]) for j in range(len(df.index))]
                row_dict_list[i] = row_list
        return differences, row_dict_list

    def publish_row(self, chunk_length, differences, row_dict_list):
        """
        Takes data from a csv and sends data in rows to mqtt for event playback. Data is formatted as a dictionary and published
        to mqtt through small batches of rows
        """
        for i in tqdm(range(chunk_length)):
            time.sleep(float(float(differences[i])/ 1000))
            if (i % 10 == 0):
                for table in ['packet', 'dynamics', 'controls', 'pack', 'diagnostics', 'thermal']: #Through the different tables
                    end_index = min(i + 10, chunk_length)  # Ensure we don't exceed the length
                    batch_data = row_dict_list.get(table)[i:end_index]
                    self.mqtt.publish(f'data/{table}', pickle.dumps(batch_data), qos=0)

    def stream_data(self, df, table_desc, time_adjustment = True):
        result = self.setup_rows(df, table_desc, time_adjustment=time_adjustment)
        differences = result[0]
        rows = result[1]
        i = 0
        for i in range(0, len(df.index), 4000):
            mini = min(i + 4000, len(differences))
            sliced_rows = {key: value[i:mini] for key, value in rows.items()}
            yield (mini - i), differences[i:mini], sliced_rows
            i += 4000

        
if __name__ == '__main__':

    logging.basicConfig(level=logging.CRITICAL)
    # Playback testing ---------------------------------------------------------------------------------------------
    with DBHandler(unsafe=True, target=DBTarget.LOCAL) as db:
        with MQTTHandler(name ='event_playback_test', target = MQTTTarget.LOCAL, db_handler=db) as mqtt:
            #mqtt.connect()
            db.connect(target = DBTarget.LOCAL, user = 'electric')
            dataSender = CSVToDB("2024_10_13__001_AutoXCompDay", db_handler=db, mqtt=mqtt)
            table_desc = get_table_column_specs()
            ## Event playback functionarlity code---------------------------------------------------------------------------------
            dataSender.event_seperator(threshold=5) #Saves list to harddrive
            mqtt.connect()
            for chunk, differences, rows in dataSender.stream_data(pd.read_csv(Path.cwd().joinpath("event_csv").joinpath("8.csv")), table_desc=table_desc):
                dataSender.publish_row(chunk, differences, rows)
            
            shutil.rmtree(Path.cwd().joinpath("event_csv"))

            # Inserting data into the database for efficiency. Batch Sending Code ---------------------------------------------------
            # for chunk, differences, rows in tqdm(dataSender.stream_data(dataSender.combine_all_csv(), table_desc=table_desc, time_adjustment=False)):
            #     dataSender.insert_multi_row_from_csv(chunk, rows)
            # dataSender.insert_multi_row_from_csv(csv_folder, table_desc=table_desc)


    # TODO event sepearation visualizations
    # for i in range(len(test)):
    #     flw = test[i]["Front Left Wheel Speed"]
    #     time = test[i]["Time"]

    #     plt.figure(figsize=(10, 6))
    #     plt.plot(time, flw, label="Front Left Wheel Speed", color="blue", linewidth=2)

    #     # Adding labels, title, and legend
    #     plt.title("Front Left Wheel Speed vs. Time", fontsize=16)
    #     plt.xlabel("Time (s)", fontsize=14)
    #     plt.ylabel("Front Left Wheel Speed (units)", fontsize=14)
    #     plt.legend(fontsize=12)
    #     plt.grid(True, linestyle='--', alpha=0.7)

    #     # Show the plot
    #     plt.tight_layout()
    #     plt.show()
    #     plt.close()



    
      
