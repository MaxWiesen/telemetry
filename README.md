Please reference LHR/Electronics/Telemetry/Database OneNote for information on this repo.

Notes:
When rebuilding SQL script, add following function to pgmodeler output: 
```
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
```
Immediately after:
```
SET check_function_bodies = false;
-- ddl-end --
```