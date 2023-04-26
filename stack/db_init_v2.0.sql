-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 1.0.1
-- PostgreSQL version: 15.0
-- Project Site: pgmodeler.io
-- Model Author: ---
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
-- 	 PASSWORD '2fast2quick';
-- -- ddl-end --
-- 
-- object: grafana | type: ROLE --
-- DROP ROLE IF EXISTS grafana;
CREATE ROLE grafana WITH 
	LOGIN
	 PASSWORD 'frontend'
	CONNECTION LIMIT 5;
-- ddl-end --

-- object: analysis | type: ROLE --
-- DROP ROLE IF EXISTS analysis;
CREATE ROLE analysis WITH 
	LOGIN
	 PASSWORD 'north_dakota'
	CONNECTION LIMIT 5;
-- ddl-end --


-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: telemetry | type: DATABASE --
-- DROP DATABASE IF EXISTS telemetry;
-- CREATE DATABASE telemetry
-- 	OWNER = electric;
-- ddl-end --


SET check_function_bodies = false;
-- ddl-end --

-- object: public.get_event_index | type: FUNCTION --
-- DROP FUNCTION IF EXISTS public.get_event_index(smallint,smallint) CASCADE;
CREATE OR REPLACE FUNCTION public.get_event_index (car smallint, day smallint)
	RETURNS smallint
	LANGUAGE plpgsql
	IMMUTABLE
	STRICT
	AS
$$
DECLARE ind smallint;
BEGIN
	SELECT COUNT(event_id)
	INTO ind
	FROM event
	WHERE car_id = car AND day_id = day;
	RETURN ind + 1;
END;
$$;
-- ddl-end --
ALTER FUNCTION public.get_event_index(smallint,smallint) OWNER TO electric;
-- ddl-end --

-- object: public.drive_day | type: TABLE --
-- DROP TABLE IF EXISTS public.drive_day CASCADE;
CREATE TABLE public.drive_day (
	day_id smallserial NOT NULL,
	date date NOT NULL,
	power_limit integer,
	conditions text,
	CONSTRAINT drive_day_pk PRIMARY KEY (day_id)
);
-- ddl-end --
ALTER TABLE public.drive_day OWNER TO electric;
-- ddl-end --

-- object: public.lut_driver | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_driver CASCADE;
CREATE TABLE public.lut_driver (
	driver_id smallint NOT NULL,
	driver_name text NOT NULL,
	driver_weight smallint,
	CONSTRAINT lut_driver_pk PRIMARY KEY (driver_id)
);
-- ddl-end --
ALTER TABLE public.lut_driver OWNER TO electric;
-- ddl-end --

INSERT INTO public.lut_driver (driver_id, driver_name, driver_weight) VALUES (E'0', E'Other', DEFAULT);
-- ddl-end --
INSERT INTO public.lut_driver (driver_id, driver_name, driver_weight) VALUES (E'1', E'Jaiden Patel', DEFAULT);
-- ddl-end --
INSERT INTO public.lut_driver (driver_id, driver_name, driver_weight) VALUES (E'2', E'Sohan Agnihotri', DEFAULT);
-- ddl-end --
INSERT INTO public.lut_driver (driver_id, driver_name, driver_weight) VALUES (E'3', E'Dylan Hammerback', DEFAULT);
-- ddl-end --
INSERT INTO public.lut_driver (driver_id, driver_name, driver_weight) VALUES (E'4', E'Andrew Zhang', DEFAULT);
-- ddl-end --
INSERT INTO public.lut_driver (driver_id, driver_name, driver_weight) VALUES (E'5', E'Ali Jensen', DEFAULT);
-- ddl-end --

-- object: public.lut_location | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_location CASCADE;
CREATE TABLE public.lut_location (
	location_id smallint NOT NULL,
	area text NOT NULL,
	track text NOT NULL,
	CONSTRAINT lut_location_pk PRIMARY KEY (location_id)
);
-- ddl-end --
ALTER TABLE public.lut_location OWNER TO electric;
-- ddl-end --

INSERT INTO public.lut_location (location_id, area, track) VALUES (E'0', E'Other', E'Other');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, track) VALUES (E'1', E'Pickle', E'Innovation Blvd');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, track) VALUES (E'2', E'Pickle', E'North Lot');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, track) VALUES (E'3', E'Pickle', E'South Lot');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, track) VALUES (E'4', E'COTA', E'Lot J');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, track) VALUES (E'5', E'COTA', E'Lot H');
-- ddl-end --
INSERT INTO public.lut_location (location_id, area, track) VALUES (E'6', E'COTA', E'Go Kart Track');
-- ddl-end --

-- object: public.lut_car | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_car CASCADE;
CREATE TABLE public.lut_car (
	car_id smallint NOT NULL,
	car_name text NOT NULL,
	CONSTRAINT lut_car_pk PRIMARY KEY (car_id)
);
-- ddl-end --
ALTER TABLE public.lut_car OWNER TO electric;
-- ddl-end --

INSERT INTO public.lut_car (car_id, car_name) VALUES (E'1', E'Easy Driver');
-- ddl-end --
INSERT INTO public.lut_car (car_id, car_name) VALUES (E'2', E'Lady Luck');
-- ddl-end --

-- object: public.lut_event_type | type: TABLE --
-- DROP TABLE IF EXISTS public.lut_event_type CASCADE;
CREATE TABLE public.lut_event_type (
	type_id smallint NOT NULL,
	event_type text NOT NULL,
	CONSTRAINT lut_event_type_pk PRIMARY KEY (type_id)
);
-- ddl-end --
ALTER TABLE public.lut_event_type OWNER TO electric;
-- ddl-end --

INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'0', E'Other');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'1', E'Endurance');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'2', E'Autocross');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'3', E'Skidpad');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'4', E'Straightline Acceleration');
-- ddl-end --
INSERT INTO public.lut_event_type (type_id, event_type) VALUES (E'5', E'Straightline Breaking');
-- ddl-end --

-- object: public.event | type: TABLE --
-- DROP TABLE IF EXISTS public.event CASCADE;
CREATE TABLE public.event (
	event_id smallserial NOT NULL,
	day_id smallint NOT NULL,
	creation_time bigint NOT NULL,
	start_time bigint,
	end_time bigint,
	car_id smallint NOT NULL,
	driver_id smallint NOT NULL,
	location_id smallint NOT NULL,
	event_type smallint NOT NULL,
	event_index smallint GENERATED ALWAYS AS (public.get_event_index(car_id, day_id)) STORED,
	car_weight smallint,
	tow_angle real,
	camber real,
	ride_height real,
	ackerman_adjustment real,
	shock_dampening smallint,
	power_limit integer,
	torque_limit smallint,
	fr_pressure real,
	fl_pressure real,
	br_pressure real,
	bl_pressure real,
	front_wing_on boolean,
	rear_wing_on boolean,
	regen_on boolean,
	undertray_on boolean,
	CONSTRAINT event_pk PRIMARY KEY (event_id)
);
-- ddl-end --
ALTER TABLE public.event OWNER TO electric;
-- ddl-end --

-- object: public.dynamics | type: TABLE --
-- DROP TABLE IF EXISTS public.dynamics CASCADE;
CREATE TABLE public.dynamics (
	"time" bigint NOT NULL,
	frw_acc double precision[],
	flw_acc double precision[],
	brw_acc double precision[],
	blw_acc double precision[],
	body1_acc double precision[],
	body1_ang double precision[],
	body2_ang double precision[],
	body2_acc double precision[],
	body3_acc double precision[],
	body3_ang double precision[],
	accel_pedal_pos real,
	brake_pressure real,
	motor_rpm integer,
	torque_command smallint,
	gps point

);
-- ddl-end --
ALTER TABLE public.dynamics OWNER TO electric;
-- ddl-end --

-- object: public.power | type: TABLE --
-- DROP TABLE IF EXISTS public.power CASCADE;
CREATE TABLE public.power (
	"time" bigint NOT NULL,
	bms_cells_v real[],
	pack_voltage real,
	pack_current real,
	lv_cells_v real[],
	lv_voltage real,
	lv_current real,
	ambient_temp real,
	bms_pack_temp jsonb[],
	bms_balancing_temp jsonb[],
	fan_speed jsonb[],
	inline_cooling_temp real,
	cooling_flow real

);
-- ddl-end --
ALTER TABLE public.power OWNER TO electric;
-- ddl-end --

-- object: public.electronics | type: TABLE --
-- DROP TABLE IF EXISTS public.electronics CASCADE;
CREATE TABLE public.electronics (
	"time" bigint NOT NULL,
	imd_on boolean,
	hv_contactor_on boolean,
	pre_c_contactor_on boolean,
	ls_contactor_on boolean,
	lv_battery_status smallint

);
-- ddl-end --
ALTER TABLE public.electronics OWNER TO electric;
-- ddl-end --


-- object: "FK_day_id" | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS "FK_day_id" CASCADE;
ALTER TABLE public.event ADD CONSTRAINT "FK_day_id" FOREIGN KEY (day_id)
REFERENCES public.drive_day (day_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "FK_car_id" | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS "FK_car_id" CASCADE;
ALTER TABLE public.event ADD CONSTRAINT "FK_car_id" FOREIGN KEY (car_id)
REFERENCES public.lut_car (car_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "FK_driver_id" | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS "FK_driver_id" CASCADE;
ALTER TABLE public.event ADD CONSTRAINT "FK_driver_id" FOREIGN KEY (driver_id)
REFERENCES public.lut_driver (driver_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "FK_location_id" | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS "FK_location_id" CASCADE;
ALTER TABLE public.event ADD CONSTRAINT "FK_location_id" FOREIGN KEY (location_id)
REFERENCES public.lut_location (location_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --

-- object: "FK_event_type" | type: CONSTRAINT --
-- ALTER TABLE public.event DROP CONSTRAINT IF EXISTS "FK_event_type" CASCADE;
ALTER TABLE public.event ADD CONSTRAINT "FK_event_type" FOREIGN KEY (event_type)
REFERENCES public.lut_event_type (type_id) MATCH SIMPLE
ON DELETE NO ACTION ON UPDATE NO ACTION;
-- ddl-end --


