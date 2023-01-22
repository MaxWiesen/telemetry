-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 0.9.4
-- PostgreSQL version: 13.0
-- Project Site: pgmodeler.io
-- Model Author: Max Wiesenfeld
-- Project Version: v1.2.0
-- object: grafana | type: ROLE --
-- DROP ROLE IF EXISTS grafana;
CREATE ROLE grafana WITH 
	LOGIN
	ENCRYPTED PASSWORD 'frontend'
	CONNECTION LIMIT 5;
-- ddl-end --

-- -- object: electric | type: ROLE --
-- -- DROP ROLE IF EXISTS electric;
-- CREATE ROLE electric WITH
-- 	SUPERUSER
-- 	CREATEDB
-- 	CREATEROLE
-- 	INHERIT
-- 	LOGIN
-- 	REPLICATION
-- 	BYPASSRLS
-- 	ENCRYPTED PASSWORD '2fast2quick';
-- -- ddl-end --
--
-- object: analysis | type: ROLE --
-- DROP ROLE IF EXISTS analysis;
CREATE ROLE analysis WITH
	LOGIN
	ENCRYPTED PASSWORD 'north_dakota';
-- ddl-end --


-- Database creation must be performed outside a multi lined SQL file.
-- These commands were put in this file only as a convenience.
--
-- -- object: telemetry | type: DATABASE --
-- -- DROP DATABASE IF EXISTS telemetry;
-- CREATE DATABASE telemetry
-- 	OWNER = electric;
-- -- ddl-end --
--

-- object: public.event | type: TABLE --
-- DROP TABLE IF EXISTS public.event CASCADE;
CREATE TABLE public.event (
	event_id smallint NOT NULL GENERATED ALWAYS AS IDENTITY ,
	creation_time timestamptz,
	start_time timestamptz,
	end_time timestamptz,
	drive_day smallint,
	driver smallint,
	location smallint,
	event_index smallint,
	day_id_drive_day smallint NOT NULL,
	driver_id_lut_driver smallint NOT NULL,
	location_id_lut_location smallint NOT NULL,
	event_type smallint,
	car_weight smallint,
	front_wing_on boolean,
	regen_on boolean,
	tow_angle real,
	camber real,
	ride_height real,
	ackerman_adjustment real,
	tire_pressure real,
	blade_arb_stiffness real,
	power_output smallint,
	toque_output smallint,
	shock_dampening smallint,
	rear_wing_on boolean,
	undertray_on boolean,
	type_id_lut_event_type smallint NOT NULL,
	CONSTRAINT event_pk PRIMARY KEY (event_id)
);
-- ddl-end --
COMMENT ON COLUMN public.event.event_id IS E'Event ID Number';
-- ddl-end --
COMMENT ON COLUMN public.event.creation_time IS E'Timestamp reflecting the creation_time of the event';
-- ddl-end --
COMMENT ON COLUMN public.event.start_time IS E'Represents event start time';
-- ddl-end --
COMMENT ON COLUMN public.event.end_time IS E'Represents event end time';
-- ddl-end --
COMMENT ON COLUMN public.event.drive_day IS E'Joins drive_day table';
-- ddl-end --
COMMENT ON COLUMN public.event.driver IS E'Represents event''s driver''s name';
-- ddl-end --
COMMENT ON COLUMN public.event.location IS E'Corresponds to lut_location for location lookup';
-- ddl-end --
COMMENT ON COLUMN public.event.event_index IS E'Represents which number event this is in the work day.';
-- ddl-end --
COMMENT ON COLUMN public.event.event_type IS E'Joins lut_event_type for event context';
-- ddl-end --
ALTER TABLE public.event OWNER TO electric;
-- ddl-end --

-- object: public.drive_day | type: TABLE --
-- DROP TABLE IF EXISTS public.drive_day CASCADE;
CREATE TABLE public.drive_day (
	day_id smallserial NOT NULL,
	conditions text,
	power_limit double precision,
	CONSTRAINT drive_day_pk PRIMARY KEY (day_id)
);
-- ddl-end --
COMMENT ON COLUMN public.drive_day.day_id IS E'Represents the enum day';
-- ddl-end --
ALTER TABLE public.drive_day OWNER TO electric;
-- ddl-end --

-- object: drive_day_fk | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS drive_day_fk CASCADE;
ALTER TABLE public.event ADD CONSTRAINT drive_day_fk FOREIGN KEY (day_id_drive_day)
REFERENCES public.drive_day (day_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: public.dynamics | type: TABLE --
-- DROP TABLE IF EXISTS public.dynamics CASCADE;
CREATE TABLE public.dynamics (
	event_id smallint NOT NULL,
	event_id_event smallint NOT NULL,
	"time" timestamptz,
	body_acc_x double precision,
	body_acc_y double precision,
	body_acc_z double precision,
	body_ang_x double precision,
	body_ang_y double precision,
	body_ang_z double precision,
	fr_acc_x double precision,
	fr_acc_y double precision,
	fr_acc_z double precision,
	fl_acc_x double precision,
	fl_acc_y double precision,
	fl_acc_z double precision,
	br_acc_x double precision,
	br_acc_y double precision,
	br_acc_z double precision,
	bl_acc_x double precision,
	bl_acc_y double precision,
	bl_acc_z double precision,
	torque_command double precision,
	motor_rpm bigint,
	tire_temp double precision,
	brake_rotor_temp double precision,
	gps point,
	CONSTRAINT dynamics_pk PRIMARY KEY (event_id)
);
-- ddl-end --
COMMENT ON TABLE public.dynamics IS E'This table contains sensor data relating to dynamics team';
-- ddl-end --
COMMENT ON COLUMN public.dynamics.event_id IS E'Represents the event section ID';
-- ddl-end --
COMMENT ON COLUMN public.dynamics.body_acc_x IS E'Represents body IMU''s acceleration in the x direction';
-- ddl-end --
COMMENT ON COLUMN public.dynamics.body_ang_x IS E'This represents the body IMU''s angular velocity in the x direction';
-- ddl-end --
COMMENT ON COLUMN public.dynamics.fr_acc_x IS E'Represent front-right wheel IMU''s acceleration in the x-direction';
-- ddl-end --
ALTER TABLE public.dynamics OWNER TO electric;
-- ddl-end --

-- object: event_fk | type: CONSTRAINT --
-- ALTER TABLE public.dynamics DROP CONSTRAINT IF EXISTS event_fk CASCADE;
ALTER TABLE public.dynamics ADD CONSTRAINT event_fk FOREIGN KEY (event_id_event)
REFERENCES public.event (event_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: public.power | type: TABLE --
-- DROP TABLE IF EXISTS public.power CASCADE;
CREATE TABLE public.power (
	event_id smallint NOT NULL,
	event_id_event smallint NOT NULL,
	"time" timestamptz,
	pack_voltage double precision,
	pack_current double precision,
	dcdc_current double precision,
	ambient_temp double precision,
	bms_pack_temp double precision,
	bms_balancing_temp double precision,
	contactor_status boolean,
	bms_cells_v real[][],
	fan_speed bigint,
	inline_cooling_temp double precision,
	cooling_flow double precision,
	CONSTRAINT power_pk PRIMARY KEY (event_id)
);
-- ddl-end --
COMMENT ON TABLE public.power IS E'With great power comes great responsibility...and a lot of fun.';
-- ddl-end --
ALTER TABLE public.power OWNER TO electric;
-- ddl-end --

-- object: event_fk | type: CONSTRAINT --
-- ALTER TABLE public.power DROP CONSTRAINT IF EXISTS event_fk CASCADE;
ALTER TABLE public.power ADD CONSTRAINT event_fk FOREIGN KEY (event_id_event)
REFERENCES public.event (event_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: public.lut_event_type | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_event_type CASCADE;
CREATE TABLE public.lut_event_type (
	type_id smallint NOT NULL,
	event_type text,
	CONSTRAINT lut_event_type_pk PRIMARY KEY (type_id)
);
-- ddl-end --
COMMENT ON TABLE public.lut_event_type IS E'Look up table for event types';
-- ddl-end --
ALTER TABLE public.lut_event_type OWNER TO electric;
-- ddl-end --

INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'0', E'Endurance');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'1', E'Autocross');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'2', E'Skidpad');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'3', E'Straightline Acceleration');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'4', E'Straightline Breaking');
-- ddl-end --

-- object: public.lut_location | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_location CASCADE;
CREATE TABLE public.lut_location (
	location_id smallint NOT NULL,
	area text,
	location text,
	CONSTRAINT lut_location_pk PRIMARY KEY (location_id)
);
-- ddl-end --
COMMENT ON TABLE public.lut_location IS E'This lookup table links locations with their IDs.';
-- ddl-end --
ALTER TABLE public.lut_location OWNER TO electric;
-- ddl-end --

INSERT INTO public.lut_location (location_id, area, location) VALUES (E'0', E'Pickle', E'Innovation Blvd');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, location) VALUES (E'1', E'Pickle', E'Front Lot');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, location) VALUES (E'2', E'Pickle', E'Other Lot');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, location) VALUES (E'3', E'COTA', E'Lot J');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, location) VALUES (E'4', E'COTA', E'Lot H');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, location) VALUES (E'5', E'COTA', E'Go Kart Track');
-- ddl-end --

-- object: public.lut_driver | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_driver CASCADE;
CREATE TABLE public.lut_driver (
	driver_id smallint NOT NULL,
	name text,
	driver_weight smallint,
	CONSTRAINT lut_driver_pk PRIMARY KEY (driver_id)
);
-- ddl-end --
COMMENT ON TABLE public.lut_driver IS E'Lookup table for driver names';
-- ddl-end --
ALTER TABLE public.lut_driver OWNER TO electric;
-- ddl-end --

-- object: lut_driver_fk | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS lut_driver_fk CASCADE;
ALTER TABLE public.event ADD CONSTRAINT lut_driver_fk FOREIGN KEY (driver_id_lut_driver)
REFERENCES public.lut_driver (driver_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: lut_location_fk | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS lut_location_fk CASCADE;
ALTER TABLE public.event ADD CONSTRAINT lut_location_fk FOREIGN KEY (location_id_lut_location)
REFERENCES public.lut_location (location_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: public.part_revs | type: TABLE --
-- DROP TABLE IF EXISTS public.part_revs CASCADE;
CREATE TABLE public.part_revs (
	event_id smallint NOT NULL,
	event_id_event smallint NOT NULL,
	CONSTRAINT lut_part_revs_pk PRIMARY KEY (event_id)
);
-- ddl-end --
ALTER TABLE public.part_revs OWNER TO electric;
-- ddl-end --

-- object: event_fk | type: CONSTRAINT --
-- ALTER TABLE public.part_revs DROP CONSTRAINT IF EXISTS event_fk CASCADE;
ALTER TABLE public.part_revs ADD CONSTRAINT event_fk FOREIGN KEY (event_id_event)
REFERENCES public.event (event_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: part_revs_uq | type: CONSTRAINT --
-- ALTER TABLE public.part_revs DROP CONSTRAINT IF EXISTS part_revs_uq CASCADE;
ALTER TABLE public.part_revs ADD CONSTRAINT part_revs_uq UNIQUE (event_id_event);
-- ddl-end --

-- object: public.electronics | type: TABLE --
-- DROP TABLE IF EXISTS public.electronics CASCADE;
CREATE TABLE public.electronics (
	event_id smallint NOT NULL,
	"time" timestamptz,
	imd_on boolean,
	hv_contactor_on boolean,
	pre_c_contactor_on boolean,
	pcb_temps jsonb,
	event_id_event smallint NOT NULL,
	CONSTRAINT electronics_pk PRIMARY KEY (event_id)
);
-- ddl-end --
ALTER TABLE public.electronics OWNER TO electric;
-- ddl-end --

-- object: event_fk | type: CONSTRAINT --
-- ALTER TABLE public.electronics DROP CONSTRAINT IF EXISTS event_fk CASCADE;
ALTER TABLE public.electronics ADD CONSTRAINT event_fk FOREIGN KEY (event_id_event)
REFERENCES public.event (event_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: lut_event_type_fk | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS lut_event_type_fk CASCADE;
ALTER TABLE public.event ADD CONSTRAINT lut_event_type_fk FOREIGN KEY (type_id_lut_event_type)
REFERENCES public.lut_event_type (type_id) MATCH FULL
ON DELETE RESTRICT ON UPDATE CASCADE;
-- ddl-end --

-- object: timezone | type: Generic SQL Object --
SET TIME ZONE 'CST';
-- ddl-end --


