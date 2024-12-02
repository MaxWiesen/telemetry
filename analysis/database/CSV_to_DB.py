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
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from tqdm import tqdm
from psycopg.types.json import Jsonb

sys.path.append(str(Path(__file__).parents[2]))

from analysis.sql_utils.db_handler import get_table_column_specs
from analysis.sql_utils.db_handler import DBHandler, DBTarget
from stack.ingest.mqtt_handler import MQTTHandler, MQTTTarget

class csv_to_db():

    def __init__(self, data_csv_folder, db_handler = None, MQQT_target = MQTTTarget.LOCAL):
        self.db_handler = db_handler
        self.MQTT_target = MQQT_target
        try:
            self.data_csv_folder = list(Path.cwd().joinpath("csv_data", data_csv_folder).glob("*.csv"))
        except FileNotFoundError:
            logging.warning("NO FOLDER OF CSV FILES WERE SPECIFIED. ENSURE A FOLDER IS SELECTED OR DATA IS IN csv_data")
            self.data_csv_folder = list(Path.cwd().joinpath("csv_data").glob("*.csv"))

        try:
            self.mqtt_handler = MQTTHandler(name='sam_test', target=self.MQTT_target, db_handler=None)
        except Exception as e:
            self.mqtt_handler = None
            logging.warning("mqtt_handler object failed to initialize")

    def get_data_csv_folder(self):
        return [pd.read_csv(self.data_csv_folder[i]) for i in range(len(self.data_csv_folder))]

    def event_seperator(self, threshold = 20):
        """"
        The class variable is a directory containing csv files from a certain drive day. The goal of this method is to 
        partition the folder into continous segments in which the car is running, outputting a list containing dataframes
        where each dataframe represents a near continouse time period in which the car is running. 
        """
        continous_event = []
        event = [pd.read_csv(self.data_csv_folder[0])]
        df_current = pd.read_csv(self.data_csv_folder[0])
        for csv_path in tqdm(range(len(self.data_csv_folder) -1)):
            #df_current = pd.read_csv(self.data_csv_folder[csv_path])
            df_forw = pd.read_csv(self.data_csv_folder[csv_path+1])

            #df_current["Year"] = df_current["Year"] + 2000
            dt = pd.to_datetime({"year" : df_current["Year"] + 2000, 
                "month" : df_current["Month"], 
                "day" : df_current["Day"], 
                "hour" : df_current["Hour"], 
                "minute" : df_current["Minute"], 
                "second" : df_current["Seconds"], 
                "millisecond" : df_current["Milliseconds"]}).astype(int) // 1000000 #gets into ms
            last_dt_current = dt.to_list()[-1]

            #df_forw["Year"] = df_forw["Year"] + 2000
            dt = pd.to_datetime({"year" : df_forw["Year"] + 2000, 
                "month" : df_forw["Month"], 
                "day" : df_forw["Day"], 
                "hour" : df_forw["Hour"], 
                "minute" : df_forw["Minute"], 
                "second" : df_forw["Seconds"], 
                "millisecond" : df_forw["Milliseconds"]}).astype(int) // 1000000 #gets into ms
            first_dt_forw = dt.to_list()[0]

            if (first_dt_forw - last_dt_current < (threshold * 1000)):
                differences = [df_forw["Time"][i] - df_forw["Time"][i-1] for i in range(1, len(df_forw.index))]
                df_forw["Time"][0] = df_current["Time"].iloc[-1] + ((first_dt_forw - last_dt_current)//1000) #Find differing times
                for i in range(1, len(df_forw.index)):
                    df_forw["Time"][i] = df_forw["Time"][i-1] + differences[i-1]
                df_current = df_forw
                event.append(df_forw)
            else:
                continous_event.append(pd.concat(event, ignore_index=True))
                event = [df_forw]
                df_current = df_forw
                if (csv_path == len(self.data_csv_folder) - 2):
                    continous_event.append(pd.concat(event))

        return continous_event


    def get_Tables(self):
        """
        Creates a dictionary based on get_table_column_specs to hold data to be added to the database
        """
        ent = get_table_column_specs()
        for i in ent.keys():
            for j in ent.get(i).keys():
                ent.get(i).update({j : []})
        return ent

        
    def enumerate_packet_id(self, data_csv):       
        """
        Enumerates the packet_id from the last known packet_id. Uses the csv with car data to determine amount of packet_id to add
        """
        try: 
            #last_packet    
            last_packet = DBHandler.simple_select("SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1", target=DBTarget.LOCAL, user='electric', handler=self.db_handler)[0][0]
        except IndexError:
            last_packet = 1

        df = data_csv
        pack_id = list(range(last_packet + 1, last_packet+1+len(df.index)))
        return pack_id

    def dataConvert(self, data_csv):
        """
        Converts data to the csv to a format that can be added into the database
        """
        ent = get_table_column_specs()
        items = []
        for i in ent.keys():
            items.extend(ent.get(i).keys())
        items = list(set(items))
        convert = {}
        df = data_csv
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
                    df["Year"] = df["Year"] + 2000

                    dt = pd.to_datetime({"year" : df["Year"], 
                        "month" : df["Month"], 
                        "day" : df["Day"], 
                        "hour" : df["Hour"], 
                        "minute" : df["Minute"], 
                        "second" : df["Seconds"], 
                        "millisecond" : df["Milliseconds"]}).astype(int) // 1000000 #gets into ms
                    first_dt = dt.to_list()[0]
                    offset = df["Time"][0] * 1000 #get into ms

                    dt_list = []
                    for j in range(len(df.index)):
                        dt_list.append(int(first_dt - offset + (df["Time"][j] * 1000)))
                    
                    convert.update({i : dt_list})
                    
                    logging.info(i + ": added")
                case "torque_request":
                    df["Inverter Torque Request"] = df["Inverter Torque Request"].astype("float32")
                    convert.update({i : df["Inverter Torque Request"].to_list()})
                    logging.info(i + ": added")
                case "vcu_position":
                    df["Vehicle Displacement X"] = df["Vehicle Displacement X"].astype("float32")
                    df["Vehicle Displacement Y"] = df["Vehicle Displacement Y"].astype("float32")
                    df["Vehicle Displacement Z"] = df["Vehicle Displacement Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Vehicle Displacement X"], df["Vehicle Displacement Y"], df["Vehicle Displacement Z"])]})
                    logging.info(i + ": added")
                case "vcu_velocity":
                    df["Vehicle Velocity X"] = df["Vehicle Velocity X"].astype("float32")
                    df["Vehicle Velocity Y"] = df["Vehicle Velocity Y"].astype("float32")
                    df["Vehicle Velocity Z"] = df["Vehicle Velocity Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Vehicle Velocity X"], df["Vehicle Velocity Y"], df["Vehicle Velocity Z"])]})
                    logging.info(i + ": added")
                case "vcu_accel":
                    df["Vehicle Acceleration X"] = df["Vehicle Acceleration X"].astype("float32")
                    df["Vehicle Acceleration Y"] = df["Vehicle Acceleration Y"].astype("float32")
                    df["Vehicle Acceleration Z"] = df["Vehicle Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Vehicle Acceleration X"], df["Vehicle Acceleration Y"], df["Vehicle Acceleration Z"])]})
                    logging.info(i + ": added")
                case "gps":
                    df["Latitude"] = df["Latitude"].astype("float64")
                    df["Longitude"] = df["Longitude"].astype("float64")
                    convert.update({i : [(x,y) for x, y in zip(df["Longitude"], df["Latitude"])]})
                    logging.info(i + ": added")
                case "gps_velocity":
                    df["Speed"] = df["Speed"].astype("float32")
                    convert.update({i : df["Speed"].to_list()})
                    logging.info(i + ": added")
                case "gps_heading":
                    df["Heading"] = df["Heading"].astype("float32")
                    convert.update({i : df["Heading"].to_list()})
                    logging.info(i + ": added")
                case "body1_accel":
                    df["VCU Acceleration X"] = df["VCU Acceleration X"].astype("float32")
                    df["VCU Acceleration Y"] = df["VCU Acceleration Y"].astype("float32")
                    df["VCU Acceleration Z"] = df["VCU Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["VCU Acceleration X"], df["VCU Acceleration Y"], df["VCU Acceleration Z"])]})
                    logging.info(i + ": added")
                case "body2_accel":
                    df["HVC Acceleration X"] = df["HVC Acceleration X"].astype("float32")
                    df["HVC Acceleration Y"] = df["HVC Acceleration Y"].astype("float32")
                    df["HVC Acceleration Z"] = df["HVC Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["HVC Acceleration X"], df["HVC Acceleration Y"], df["HVC Acceleration Z"])]})
                    logging.info(i + ": added")
                case "body3_accel":
                    df["PDU Acceleration X"] = df["PDU Acceleration X"].astype("float32")
                    df["PDU Acceleration Y"] = df["PDU Acceleration Y"].astype("float32")
                    df["PDU Acceleration Z"] = df["PDU Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["PDU Acceleration X"], df["PDU Acceleration Y"], df["PDU Acceleration Z"])]})
                    logging.info(i + ": added")
                case "flw_accel":
                    df["Front Left Acceleration X"] = df["Front Left Acceleration X"].astype("float32")
                    df["Front Left Acceleration Y"] = df["Front Left Acceleration Y"].astype("float32")
                    df["Front Left Acceleration Z"] = df["Front Left Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Front Left Acceleration X"], df["Front Left Acceleration Y"], df["Front Left Acceleration Z"])]})
                    logging.info(i + ": added")
                case "frw_accel":
                    df["Front Right Acceleration X"] = df["Front Right Acceleration X"].astype("float32")
                    df["Front Right Acceleration Y"] = df["Front Right Acceleration Y"].astype("float32")
                    df["Front Right Acceleration Z"] = df["Front Right Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Front Right Acceleration X"], df["Front Right Acceleration Y"], df["Front Right Acceleration Z"])]})
                    logging.info(i + ": added")
                case "blw_accel":
                    df["Back Left Acceleration X"] = df["Back Left Acceleration X"].astype("float32")
                    df["Back Left Acceleration Y"] = df["Back Left Acceleration Y"].astype("float32")
                    df["Back Left Acceleration Z"] = df["Back Left Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Back Left Acceleration X"], df["Back Left Acceleration Y"], df["Back Left Acceleration Z"])]})
                    logging.info(i + ": added")
                case "brw_accel":
                    df["Back Right Acceleration X"] = df["Back Right Acceleration X"].astype("float32")
                    df["Back Right Acceleration Y"] = df["Back Right Acceleration Y"].astype("float32")
                    df["Back Right Acceleration Z"] = df["Back Right Acceleration Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["Back Right Acceleration X"], df["Back Right Acceleration Y"], df["Back Right Acceleration Z"])]})
                    logging.info(i + ": added")
                case "body1_gyro":
                    df["VCU Gyro X"] = df["VCU Gyro X"].astype("float32")
                    df["VCU Gyro Y"] = df["VCU Gyro Y"].astype("float32")
                    df["VCU Gyro Z"] = df["VCU Gyro Z"].astype("float32")
                    convert.update({ i : [list(a) for a in zip(df["VCU Gyro X"], df["VCU Gyro Y"], df["VCU Gyro Z"])]})
                    logging.info(i + ": added")
                case "body2_gyro":
                    df["HVC Gyro X"] = df["HVC Gyro X"].astype("float32")
                    df["HVC Gyro Y"] = df["HVC Gyro Y"].astype("float32")
                    df["HVC Gyro Z"] = df["HVC Gyro Z"].astype("float32")
                    convert.update({ i : [list(a) for a in zip(df["HVC Gyro X"], df["HVC Gyro Y"], df["HVC Gyro Z"])]})
                    logging.info(i + ": added")
                case "body3_gyro":
                    df["PDU Gyro X"] = df["PDU Gyro X"].astype("float32")
                    df["PDU Gyro Y"] = df["PDU Gyro Y"].astype("float32")
                    df["PDU Gyro Z"] = df["PDU Gyro Z"].astype("float32")
                    convert.update({i : [list(a) for a in zip(df["PDU Gyro X"], df["PDU Gyro Y"], df["PDU Gyro Z"])]})
                    logging.info(i + ": added")
                case "flw_speed":
                    df["Front Left Wheel Speed"] = df["Front Left Wheel Speed"].astype("float32")
                    convert.update({i : df["Front Left Wheel Speed"].to_list()})
                    logging.info(i + ": added")
                case "frw_speed":
                    df["Front Right Wheel Speed"] = df["Front Right Wheel Speed"].astype("float32")
                    convert.update({i : df["Front Right Wheel Speed"].to_list()})
                    logging.info(i + ": added")
                case "blw_speed":
                    df["Back Left Wheel Speed"] = df["Back Left Wheel Speed"].astype("float32")
                    convert.update({i : df["Back Left Wheel Speed"].to_list()})
                    logging.info(i + ": added")
                case "brw_speed":
                    df["Back Right Wheel Speed"] = df["Back Right Wheel Speed"].astype("float32")
                    convert.update({i : df["Back Right Wheel Speed"].to_list()})
                    logging.info(i + ": added")
                case "inverter_v":
                    df["Voltage"] = df["Voltage"].astype("float32")
                    convert.update({i : df["Voltage"].to_list()})
                    logging.info(i + ": added")
                case "inverter_c":
                    df["Current"] = df["Current"].astype("float32")
                    convert.update({i : df["Current"].to_list()})
                    logging.info(i + ": added")
                case "inverter_rpm":
                    df["RPM"] = df["RPM"].astype("Int16")
                    convert.update({i : df["RPM"].to_list()})
                    logging.info(i + ": added")
                case "inverter_torque":
                    logging.info(i + ": added")
                    df["Actual Torque"] = df["Actual Torque"].astype("float32")
                    convert.update({i : df["Actual Torque"].to_list()})
                #Skip
                case "vcu_flags":
                    logging.info(i + ": added")
                case "vcu_flags_json":
                    logging.info(i + ": added")
                case "apps1_v":
                    df["APPS 1 Voltage"] = df["APPS 1 Voltage"].astype("float32")
                    convert.update({i : df["APPS 1 Voltage"].to_list()})
                    logging.info(i + ": added")
                case "apps2_v":
                    df["APPS 2 Voltage"] = df["APPS 2 Voltage"].astype("float32")
                    convert.update({i : df["APPS 2 Voltage"].to_list()})
                    logging.info(i + ": added")
                case "bse1_v":
                    df["BSE 1 Voltage"] = df["BSE 1 Voltage"].astype("float32")
                    convert.update({i : df["BSE 1 Voltage"].to_list()})
                    logging.info(i + ": added")
                case "bse2_v":
                    df["BSE 2 Voltage"] = df["BSE 2 Voltage"].astype("float32")
                    convert.update({i : df["BSE 2 Voltage"].to_list()})
                    logging.info(i + ": added")
                case "sus1_v":
                    df["Suspension 1 Voltage"] = df["Suspension 1 Voltage"].astype("float32")
                    convert.update({i : df["Suspension 1 Voltage"].to_list()})
                    logging.info(i + ": added")
                case "sus2_v":
                    df["Suspension 2 Voltage"] = df["Suspension 2 Voltage"].astype("float32")
                    convert.update({i : df["Suspension 2 Voltage"].to_list()})
                    logging.info(i + ": added")
                case "steer_v":
                    df["Steer Voltage"] = df["Steer Voltage"].astype("float32")
                    convert.update({i : df["Steer Voltage"].to_list()})
                    logging.info(i + ": added")
                case "hv_pack_v":
                    df["Pack Voltage Mean"] = df["Pack Voltage Mean"].astype("float32")
                    convert.update({i : df["Pack Voltage Mean"].to_list()})
                    logging.info(i + ": added")
                case "hv_tractive_v":
                    df["Voltage Input into DC"] = df["Voltage Input into DC"].astype("float32")
                    convert.update({i : df["Voltage Input into DC"].to_list()})
                    logging.info(i + ": added")
                case "hv_c":
                    df["Current Input into DC"] = df["Current Input into DC"].astype("float32")
                    convert.update({i : df["Current Input into DC"].to_list()})
                    logging.info(i + ": added")
                case "lv_v":
                    df["LV Voltage"] = df["LV Voltage"].astype("float32")
                    convert.update({i : df["LV Voltage"].to_list()})
                    logging.info(i + ": added")
                case "lv_c":
                    df["LV Current"] = df["LV Current"].astype("float32")
                    convert.update({i : df["LV Current"].to_list()})
                    logging.info(i + ": added")
                case "contactor_state":
                    df["Contactor Status"] = df["Contactor Status"].astype("int16")
                    convert.update({i : df["Contactor Status"].to_list()})
                    logging.info(i + ": added")
                case "avg_cell_v":
                    df["Cell Voltage Mean"] = df["Cell Voltage Mean"].astype("float32")
                    convert.update({i : df["Cell Voltage Mean"].to_list()})
                    logging.info(i + ": added")
                case "avg_cell_temp":
                    df["Cell Temps Mean"] = df["Cell Temps Mean"].astype("float32")
                    convert.update({i : df["Cell Temps Mean"].to_list()})
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
                    df["State of Charge"] = df["State of Charge"].astype("float32")
                    convert.update({i : df["State of Charge"].to_list()})
                    logging.info(i + ": added")
                case "lv_charge_state":
                    df["LV State of Charge"] = df["LV State of Charge"].astype("float32")
                    convert.update({i:df["LV State of Charge"].to_list()})
                    logging.info(i + ": added")
                #Update with new data
                case "cells_temp":
                    try:
                        df["Segment 1 Max"] = df["Segment 1 Max"].astype("int16")
                        df["Segment 1 Min"] = df["Segment 1 Min"].astype("int16")
                        df["Segment 2 Max"] = df["Segment 2 Max"].astype("int16")
                        df["Segment 2 Min"] = df["Segment 2 Min"].astype("int16")
                        df["Segment 3 Max"] = df["Segment 3 Max"].astype("int16")
                        df["Segment 3 Min"] = df["Segment 3 Min"].astype("int16")
                        df["Segment 4 Max"] = df["Segment 4 Max"].astype("int16")
                        df["Segment 4 Min"] = df["Segment 4 Min"].astype("int16")
                        convert.update({i : [list(a) for a in zip(df["Segment 1 Max"], df["Segment 1 Min"], df["Segment 2 Max"], 
                                                                df["Segment 2 Min"], df["Segment 3 Max"], df["Segment 3 Min"],
                                                                df["Segment 4 Max"], df["Segment 4 Min"])]})
                        logging.info(i + ": added")
                    except KeyError:
                        logging.info(i + ": not included")
                case "ambient_temp":
                    logging.info(i + ": not included")
                #Resume
                case "inverter_temp":
                    df["Inverter Temp"] = df["Inverter Temp"].astype("int16")
                    convert.update({i:df["Inverter Temp"].to_list()})
                    logging.info(i + ": added")
                case "motor_temp":
                    df["Motor Temp"] = df["Motor Temp"].astype("int16")
                    convert.update({i : df["Motor Temp"].to_list()})
                    logging.info(i + ": added")
                case "water_motor_temp":
                    df["Water Temp Motor"] = df["Water Temp Motor"].astype("int16")
                    convert.update({i:df["Water Temp Motor"].to_list()})
                    logging.info(i + ": added")
                case "water_inverter_temp":
                    df["Water Temp Inverter"] = df["Water Temp Inverter"].astype("int16")
                    convert.update({i : df["Water Temp Inverter"].to_list()})
                    logging.info(i + ": added")
                case "water_rad_temp":
                    df["Water Temp Radiator"] = df["Water Temp Radiator"].astype("int16")
                    convert.update({i:df["Water Temp Radiator"].to_list()})
                    logging.info(i + ": added")
                case "rad_fan_set":
                    logging.info(i + ": added")
                case "rad_fan_rpm":
                    df["Radiator Fan RPM Percentage"] = df["Radiator Fan RPM Percentage"].astype("int16")
                    convert.update({i:df["Radiator Fan RPM Percentage"].to_list()})
                    logging.info(i + ": added")
                case "batt_fan_set":
                    logging.info(i + ": not included")
                case "batt_fan_rpm":
                    logging.info(i + ": not included")
                case "flow_rate":
                    df["Volumetric Flow Rate"] = df["Volumetric Flow Rate"].astype("int16")
                    convert.update({i:df["Volumetric Flow Rate"].to_list()})
                    logging.info(i + ": added")
        convert.update({"packet_id": self.enumerate_packet_id(data_csv)})

        fill = self.get_Tables()
        #loop through the different tables
        for i in fill.keys():
            #Loop through the column names in each table
            for j in fill.get(i).keys():
                for k in convert.keys():
                    if (k == j):
                        #Go to each table, find the columns to modify, insert new data
                        fill[i].update({k : convert.get(k)})
                    elif (k == "time" and j == "\"time\""):
                        fill[i].update({j : convert.get(k)})
        return fill

    #Each iteration makes a new connection to the database and sends a singular row at a time
    def insert_row_from_csv(self, data_csv, num_rows : int):
        """
        Adds data into the database. First adds packet table, then subsequent table using DBHandler insert function. Each iteration
        only inputs a singular row to the database, making this program the least efficient
        """
       
        df = data_csv
        data = self.dataConvert(data_csv)
        packets = data["packet"]
        #pack_list = []
        #testing with smaller data
        for i in tqdm(range(num_rows)):
            row_dict = {}
            for j in packets.keys():
                if (len(packets[j]) != 0):
                    row_dict.update({j : packets[j][i]})
            DBHandler.insert(table="packet", data=row_dict, user = "electric", handler = self.db_handler)
                    #pack_list.append(row_dict)
            logging.info(row_dict)

        for i in tqdm(data.keys()):
            if (i not in ["packet", "event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"]):
                for j in range(num_rows):
                    row_dict = {}
                    for k in data.get(i).keys():
                        if (len(data.get(i)[k]) != 0):
                            row_dict.update({k : data.get(i)[k][j]})
                            #row_list.append(row_dict)
                    logging.info(row_dict)
                
                    DBHandler.insert(table = i, data = row_dict, user="electric", handler = self.db_handler)
    def insert_multi_row_from_csv(self, data_csv, amt = 2000):
        df = data_csv
        data = self.dataConvert(data_csv)
        packets = data["packet"]
        for j in tqdm(range(0, len(df.index), amt)):
            lower = j
            pack_list = []
            if (j + amt >= len(df.index)):
                high = len(df.index)
            else:
                high = j + amt

            for i in range(lower, high, 1):
                row_dict = {}
                for j in packets.keys():
                    if (len(packets[j]) != 0):
                        row_dict.update({j : packets[j][i]})
                pack_list.append(row_dict)

            #print (pack_list) #list of dictionaries containing the data to be used
            DBHandler.insert_multi_rows(table="packet", data = pack_list, user="electric", handler = self.db_handler)
            for i in data.keys():
                row_list = []
                if (i not in ["packet", "event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"]):
                    for j in range(lower, high , 1):
                        row_dict = {}
                        for k in data.get(i).keys():
                            if (len(data.get(i)[k]) != 0):
                                row_dict.update({k : data.get(i)[k][j]})
                        row_list.append(row_dict)
                    DBHandler.insert_multi_rows(table = i, data = row_list, user="electric", handler = self.db_handler)
    def publish_row(self, data_csv):
        table_desc = get_table_column_specs()
        df = data_csv
        #df = df.head(100)
        data = self.dataConvert(data_csv)
        first_new_time = int(datetime.datetime.timestamp(datetime.datetime.now())*1000)
        differences = [data["packet"]["time"][i] - data["packet"]["time"][i-1] for i in range(1, len(df.index))]
        differences.insert(0, 0)
        data["packet"]["time"][0] = first_new_time
        for i in range(1, len(df.index)):
            data["packet"]["time"][i] = data["packet"]["time"][i-1] + differences[i]

        row_dict_list = {}
        for i in data.keys():
            row_list = []
            if (i not in ["event", "classifier", "drive_day", "lut_driver", "lut_location", "lut_car", "lut_event_type"]):
                for j in range(len(df.index)):  #Test with only 50 for now
                    row_dict = {}
                    for k in data.get(i).keys():
                        if (len(data.get(i)[k]) != 0):
                            row_dict.update({k : data.get(i)[k][j]})
                    row_list.append(DBHandler.get_insert_values(table =i, data=row_dict, table_desc=table_desc[i]))
                row_dict_list.update({i : row_list})
        #self.mqqt_handler.connect()
    
        self.mqtt_handler.connect()
        for i in tqdm(range(len(df.index))):
            time.sleep(float(float(differences[i]) / 1000))
            for table in ['packet', 'dynamics', 'controls', 'pack', 'diagnostics', 'thermal']: #Through the different tables
                self.mqtt_handler.publish(f'data/{table}', pickle.dumps(row_dict_list.get(table)[i]), qos = 0)                   
        self.mqtt_handler.disconnect()

        
if __name__ == '__main__':

    logging.basicConfig(level=logging.CRITICAL)
    # Playback testing ---------------------------------------------------------------------------------------------
    db = DBHandler(unsafe = True)
    db.connect(target = DBTarget.LOCAL, user = 'electric')
    csv = csv_to_db("10-10-2024 & 10-11-2024 Thursday Night Drive Test", db_handler=db)
    test = csv.event_seperator(threshold=5)
    # # test4 = test[0]["Time"][23790]
    # # test2 = test[0]["Time"][23791]
    # # test3 = test[0]["Time"][23792]
    csv.publish_row(test[0])
    db.kill_cnx()

    #Add a whole folder --------------------------------------------------------------------------AutoX comp day
    # db = DBHandler(unsafe=True) # 11 minutes 41 seconds, persistent connection 7 minutes 12 seconds off charger
    # db.connect(target = DBTarget.LOCAL, user = 'electric')
    # csv = csv_to_db("2024_10_13__001_AutoXCompDay", db_handler=db)
    # fold = csv.get_data_csv_folder()
    # for i in range(len(fold)):
    #     csv.insert_multi_row_from_csv(fold[i], 2000)
    # db.kill_cnx()

    # db = DBHandler(unsafe=True)
    # db.connect(target = DBTarget.LOCAL, user = 'electric')
    # last_packet = DBHandler.simple_select("SELECT packet_id FROM packet ORDER BY packet_id DESC LIMIT 1", target=DBTarget.LOCAL, user='electric', handler=db)[0][0]
    # print (last_packet)
    #Testing the single insert method for troubleshooting 
    # test_one = csv.get_data_csv_folder()[0]
    # csv.insert_row_from_csv(test_one, 100)



    
      
