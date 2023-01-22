-- Database generated with pgModeler (PostgreSQL Database Modeler).
-- pgModeler version: 0.9.4
-- PostgreSQL version: 13.0
-- Project Site: pgmodeler.io
-- Model Author: ---

-- Database creation must be performed outside a multi lined SQL file. 
-- These commands were put in this file only as a convenience.
-- 
-- object: new_database | type: DATABASE --
-- DROP DATABASE IF EXISTS new_database;
CREATE DATABASE new_database;
-- ddl-end --


-- object: public.paho_test | type: TABLE --
-- DROP TABLE IF EXISTS public.paho_test CASCADE;
CREATE TABLE public.paho_test (
	id smallserial PRIMARY KEY,
	creation_time timestamptz,
	val float

);
-- ddl-end --
COMMENT ON TABLE public.paho_test IS E'Test Schema';
-- ddl-end --
COMMENT ON COLUMN public.paho_test.id IS E'Fake ID Table';
-- ddl-end --
COMMENT ON COLUMN public.paho_test.creation_time IS E'Test time';
-- ddl-end --
COMMENT ON COLUMN public.paho_test.val IS E'Sin output value';
-- ddl-end --
ALTER TABLE public.paho_test OWNER TO electric;
-- ddl-end --


