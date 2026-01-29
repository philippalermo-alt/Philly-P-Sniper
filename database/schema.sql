--
-- PostgreSQL database dump
--

\restrict 2IGNQJsOsYxTWJ44zZpLWQ4GDxlJaNt8Lt5AzXJm7LXy2ri7ynspZRGYMxgs9rU

-- Dumped from database version 17.7
-- Dumped by pg_dump version 17.7

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: _heroku; Type: SCHEMA; Schema: -; Owner: user
--

CREATE SCHEMA _heroku;


ALTER SCHEMA _heroku OWNER TO "user";

--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: create_ext(); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.create_ext() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  schemaname TEXT;
  databaseowner TEXT;

  r RECORD;

BEGIN

  IF tg_tag OPERATOR(pg_catalog.=) 'CREATE EXTENSION' AND current_user OPERATOR(pg_catalog.!=) 'rds_superuser' THEN
    PERFORM _heroku.validate_search_path();

    FOR r IN SELECT * FROM pg_catalog.pg_event_trigger_ddl_commands()
    LOOP
        CONTINUE WHEN r.command_tag != 'CREATE EXTENSION' OR r.object_type != 'extension';

        schemaname := (
            SELECT n.nspname
            FROM pg_catalog.pg_extension AS e
            INNER JOIN pg_catalog.pg_namespace AS n
            ON e.extnamespace = n.oid
            WHERE e.oid = r.objid
        );

        databaseowner := (
            SELECT pg_catalog.pg_get_userbyid(d.datdba)
            FROM pg_catalog.pg_database d
            WHERE d.datname = pg_catalog.current_database()
        );
        --RAISE NOTICE 'Record for event trigger %, objid: %,tag: %, current_user: %, schema: %, database_owenr: %', r.object_identity, r.objid, tg_tag, current_user, schemaname, databaseowner;
        IF r.object_identity = 'address_standardizer_data_us' THEN
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'us_gaz');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'us_lex');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'us_rules');
        ELSIF r.object_identity = 'amcheck' THEN
            EXECUTE pg_catalog.format('GRANT EXECUTE ON FUNCTION %I.bt_index_check TO %I;', schemaname, databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON FUNCTION %I.bt_index_parent_check TO %I;', schemaname, databaseowner);
        ELSIF r.object_identity = 'dict_int' THEN
            EXECUTE pg_catalog.format('ALTER TEXT SEARCH DICTIONARY %I.intdict OWNER TO %I;', schemaname, databaseowner);
        ELSIF r.object_identity = 'pg_partman' THEN
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'part_config');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'part_config_sub');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'custom_time_partitions');
        ELSIF r.object_identity = 'pg_stat_statements' THEN
            EXECUTE pg_catalog.format('GRANT EXECUTE ON FUNCTION %I.pg_stat_statements_reset TO %I;', schemaname, databaseowner);
        ELSIF r.object_identity = 'postgis' THEN
            PERFORM _heroku.postgis_after_create();
        ELSIF r.object_identity = 'postgis_raster' THEN
            PERFORM _heroku.postgis_after_create();
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT', databaseowner, 'raster_columns');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT', databaseowner, 'raster_overviews');
        ELSIF r.object_identity = 'postgis_topology' THEN
            PERFORM _heroku.postgis_after_create();
            EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA topology TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA topology TO %I;', databaseowner);
            PERFORM _heroku.grant_table_if_exists('topology', 'SELECT, UPDATE, INSERT, DELETE', databaseowner);
            EXECUTE pg_catalog.format('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA topology TO %I;', databaseowner);
        ELSIF r.object_identity = 'postgis_tiger_geocoder' THEN
            PERFORM _heroku.postgis_after_create();
            EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA tiger TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tiger TO %I;', databaseowner);
            PERFORM _heroku.grant_table_if_exists('tiger', 'SELECT, UPDATE, INSERT, DELETE', databaseowner);

            EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA tiger_data TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tiger_data TO %I;', databaseowner);
            PERFORM _heroku.grant_table_if_exists('tiger_data', 'SELECT, UPDATE, INSERT, DELETE', databaseowner);
        END IF;
    END LOOP;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.create_ext() OWNER TO "user";

--
-- Name: drop_ext(); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.drop_ext() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  schemaname TEXT;
  databaseowner TEXT;

  r RECORD;

BEGIN

  IF tg_tag OPERATOR(pg_catalog.=) 'DROP EXTENSION' AND current_user OPERATOR(pg_catalog.!=) 'rds_superuser' THEN
    PERFORM _heroku.validate_search_path();

    FOR r IN SELECT * FROM pg_catalog.pg_event_trigger_dropped_objects()
    LOOP
      CONTINUE WHEN r.object_type != 'extension';

      databaseowner := (
            SELECT pg_catalog.pg_get_userbyid(d.datdba)
            FROM pg_catalog.pg_database d
            WHERE d.datname = pg_catalog.current_database()
      );

      --RAISE NOTICE 'Record for event trigger %, objid: %,tag: %, current_user: %, database_owner: %, schemaname: %', r.object_identity, r.objid, tg_tag, current_user, databaseowner, r.schema_name;

      IF r.object_identity = 'postgis_topology' THEN
          EXECUTE pg_catalog.format('DROP SCHEMA IF EXISTS topology');
      END IF;
    END LOOP;

  END IF;
END;
$$;


ALTER FUNCTION _heroku.drop_ext() OWNER TO "user";

--
-- Name: extension_before_drop(); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.extension_before_drop() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  query TEXT;

BEGIN
  query := (SELECT pg_catalog.current_query());

  -- RAISE NOTICE 'executing extension_before_drop: tg_event: %, tg_tag: %, current_user: %, session_user: %, query: %', tg_event, tg_tag, current_user, session_user, query;
  IF tg_tag OPERATOR(pg_catalog.=) 'DROP EXTENSION' AND NOT pg_catalog.pg_has_role(session_user, 'rds_superuser', 'MEMBER') THEN
    PERFORM _heroku.validate_search_path();

    -- DROP EXTENSION [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]
    IF (pg_catalog.regexp_match(query, 'DROP\s+EXTENSION\s+(IF\s+EXISTS)?.*(plpgsql)', 'i') IS NOT NULL) THEN
      RAISE EXCEPTION 'The plpgsql extension is required for database management and cannot be dropped.';
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.extension_before_drop() OWNER TO "user";

--
-- Name: grant_table_if_exists(text, text, text, text); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.grant_table_if_exists(alias_schemaname text, grants text, databaseowner text, alias_tablename text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

BEGIN
  PERFORM _heroku.validate_search_path();

  IF alias_tablename IS NULL THEN
    EXECUTE pg_catalog.format('GRANT %s ON ALL TABLES IN SCHEMA %I TO %I;', grants, alias_schemaname, databaseowner);
  ELSE
    IF EXISTS (SELECT 1 FROM pg_tables WHERE pg_tables.schemaname = alias_schemaname AND pg_tables.tablename = alias_tablename) THEN
      EXECUTE pg_catalog.format('GRANT %s ON TABLE %I.%I TO %I;', grants, alias_schemaname, alias_tablename, databaseowner);
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.grant_table_if_exists(alias_schemaname text, grants text, databaseowner text, alias_tablename text) OWNER TO "user";

--
-- Name: postgis_after_create(); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.postgis_after_create() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    schemaname TEXT;
    databaseowner TEXT;
BEGIN
    PERFORM _heroku.validate_search_path();

    schemaname := (
        SELECT n.nspname
        FROM pg_catalog.pg_extension AS e
        INNER JOIN pg_catalog.pg_namespace AS n ON e.extnamespace = n.oid
        WHERE e.extname = 'postgis'
    );
    databaseowner := (
        SELECT pg_catalog.pg_get_userbyid(d.datdba)
        FROM pg_catalog.pg_database d
        WHERE d.datname = pg_catalog.current_database()
    );

    EXECUTE pg_catalog.format('GRANT EXECUTE ON FUNCTION %I.st_tileenvelope TO %I;', schemaname, databaseowner);
    EXECUTE pg_catalog.format('GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE %I.spatial_ref_sys TO %I;', schemaname, databaseowner);
END;
$$;


ALTER FUNCTION _heroku.postgis_after_create() OWNER TO "user";

--
-- Name: validate_extension(); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.validate_extension() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  schemaname TEXT;
  r RECORD;

BEGIN

  IF tg_tag OPERATOR(pg_catalog.=) 'CREATE EXTENSION' AND current_user OPERATOR(pg_catalog.!=) 'rds_superuser' THEN
    PERFORM _heroku.validate_search_path();

    FOR r IN SELECT * FROM pg_catalog.pg_event_trigger_ddl_commands()
    LOOP
      CONTINUE WHEN r.command_tag != 'CREATE EXTENSION' OR r.object_type != 'extension';

      schemaname := (
        SELECT n.nspname
        FROM pg_catalog.pg_extension AS e
        INNER JOIN pg_catalog.pg_namespace AS n
        ON e.extnamespace = n.oid
        WHERE e.oid = r.objid
      );

      IF schemaname = '_heroku' THEN
        RAISE EXCEPTION 'Creating extensions in the _heroku schema is not allowed';
      END IF;
    END LOOP;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.validate_extension() OWNER TO "user";

--
-- Name: validate_search_path(); Type: FUNCTION; Schema: _heroku; Owner: user
--

CREATE FUNCTION _heroku.validate_search_path() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE

  current_search_path TEXT;
  schemas TEXT[];
  pg_catalog_index INTEGER;

BEGIN

  current_search_path := pg_catalog.current_setting('search_path');
  schemas := pg_catalog.string_to_array(current_search_path, ',');

  schemas := (
    SELECT pg_catalog.array_agg(TRIM(schema_name::text))
    FROM pg_catalog.unnest(schemas) AS schema_name
  );

  IF ('pg_catalog' OPERATOR(pg_catalog.=) ANY(schemas)) THEN
    SELECT pg_catalog.array_position(schemas, 'pg_catalog') INTO pg_catalog_index;
    IF pg_catalog_index OPERATOR(pg_catalog.!=) 1 THEN
      RAISE EXCEPTION 'pg_catalog must be first in the search_path for this operation. Current search_path: %', current_search_path;
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.validate_search_path() OWNER TO "user";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_settings; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.app_settings (
    key text NOT NULL,
    value text
);


ALTER TABLE public.app_settings OWNER TO "user";

--
-- Name: calibration_log; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.calibration_log (
    id integer NOT NULL,
    event_id text,
    "timestamp" timestamp without time zone,
    predicted_prob real,
    bucket text,
    outcome text DEFAULT 'PENDING'::text
);


ALTER TABLE public.calibration_log OWNER TO "user";

--
-- Name: calibration_log_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.calibration_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.calibration_log_id_seq OWNER TO "user";

--
-- Name: calibration_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.calibration_log_id_seq OWNED BY public.calibration_log.id;


--
-- Name: intelligence_log; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.intelligence_log (
    event_id text NOT NULL,
    "timestamp" timestamp without time zone,
    kickoff timestamp without time zone,
    sport text,
    teams text,
    selection text,
    odds real,
    true_prob real,
    edge real,
    outcome text DEFAULT 'PENDING'::text,
    user_bet boolean DEFAULT false,
    trigger_type text,
    stake real,
    closing_odds real,
    ticket_pct integer,
    money_pct integer,
    odds_event_id text,
    home_team text,
    away_team text,
    market text,
    line real,
    book text,
    sharp_score integer,
    user_odds real,
    user_stake real,
    home_xg real,
    away_xg real,
    dvp_rank real,
    home_adj_em real,
    away_adj_em real,
    home_adj_o real,
    away_adj_o real,
    home_adj_d real,
    away_adj_d real,
    home_tempo real,
    away_tempo real,
    home_rest integer,
    away_rest integer,
    ref_1 text,
    ref_2 text,
    ref_3 text,
    logic text
);


ALTER TABLE public.intelligence_log OWNER TO "user";

--
-- Name: matches; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.matches (
    match_id text NOT NULL,
    league text,
    season text,
    date timestamp without time zone,
    home_team text,
    away_team text,
    home_goals integer,
    away_goals integer,
    home_xg real,
    away_xg real,
    forecast_w real,
    forecast_d real,
    forecast_l real,
    scraped_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.matches OWNER TO "user";

--
-- Name: player_stats; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.player_stats (
    id integer NOT NULL,
    match_id text,
    player_id text,
    team_id text,
    player_name text,
    "position" text,
    minutes integer,
    shots integer,
    goals integer,
    assists integer,
    xg real,
    xa real,
    xg_chain real,
    xg_buildup real,
    season text,
    league text,
    scraped_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    team_name text
);


ALTER TABLE public.player_stats OWNER TO "user";

--
-- Name: player_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.player_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.player_stats_id_seq OWNER TO "user";

--
-- Name: player_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.player_stats_id_seq OWNED BY public.player_stats.id;


--
-- Name: posted_tweets; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.posted_tweets (
    id integer NOT NULL,
    sport character varying(50),
    match_name character varying(255),
    selection character varying(255),
    odds double precision,
    stake double precision,
    tweet_text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    event_id character varying(50)
);


ALTER TABLE public.posted_tweets OWNER TO "user";

--
-- Name: posted_tweets_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.posted_tweets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.posted_tweets_id_seq OWNER TO "user";

--
-- Name: posted_tweets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.posted_tweets_id_seq OWNED BY public.posted_tweets.id;


--
-- Name: calibration_log id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.calibration_log ALTER COLUMN id SET DEFAULT nextval('public.calibration_log_id_seq'::regclass);


--
-- Name: player_stats id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.player_stats ALTER COLUMN id SET DEFAULT nextval('public.player_stats_id_seq'::regclass);


--
-- Name: posted_tweets id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.posted_tweets ALTER COLUMN id SET DEFAULT nextval('public.posted_tweets_id_seq'::regclass);


--
-- Data for Name: app_settings; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- Data for Name: calibration_log; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- Data for Name: intelligence_log; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- Data for Name: matches; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- Data for Name: player_stats; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- Data for Name: posted_tweets; Type: TABLE DATA; Schema: public; Owner: user
--



--
-- Name: calibration_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.calibration_log_id_seq', 45, true);


--
-- Name: player_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.player_stats_id_seq', 162168, true);


--
-- Name: posted_tweets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.posted_tweets_id_seq', 32, true);


--
-- Name: app_settings app_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_pkey PRIMARY KEY (key);


--
-- Name: calibration_log calibration_log_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.calibration_log
    ADD CONSTRAINT calibration_log_pkey PRIMARY KEY (id);


--
-- Name: intelligence_log intelligence_log_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.intelligence_log
    ADD CONSTRAINT intelligence_log_pkey PRIMARY KEY (event_id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (match_id);


--
-- Name: player_stats player_stats_match_id_player_id_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_match_id_player_id_key UNIQUE (match_id, player_id);


--
-- Name: player_stats player_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.player_stats
    ADD CONSTRAINT player_stats_pkey PRIMARY KEY (id);


--
-- Name: posted_tweets posted_tweets_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.posted_tweets
    ADD CONSTRAINT posted_tweets_pkey PRIMARY KEY (id);


--
-- Name: intelligence_log_uniq; Type: INDEX; Schema: public; Owner: user
--

CREATE UNIQUE INDEX intelligence_log_uniq ON public.intelligence_log USING btree (odds_event_id, market, selection, line, book);


--
-- Name: extension_before_drop; Type: EVENT TRIGGER; Schema: -; Owner: user
--

CREATE EVENT TRIGGER extension_before_drop ON ddl_command_start
   EXECUTE FUNCTION _heroku.extension_before_drop();


ALTER EVENT TRIGGER extension_before_drop OWNER TO "user";

--
-- Name: log_create_ext; Type: EVENT TRIGGER; Schema: -; Owner: user
--

CREATE EVENT TRIGGER log_create_ext ON ddl_command_end
   EXECUTE FUNCTION _heroku.create_ext();


ALTER EVENT TRIGGER log_create_ext OWNER TO "user";

--
-- Name: log_drop_ext; Type: EVENT TRIGGER; Schema: -; Owner: user
--

CREATE EVENT TRIGGER log_drop_ext ON sql_drop
   EXECUTE FUNCTION _heroku.drop_ext();


ALTER EVENT TRIGGER log_drop_ext OWNER TO "user";

--
-- Name: validate_extension; Type: EVENT TRIGGER; Schema: -; Owner: user
--

CREATE EVENT TRIGGER validate_extension ON ddl_command_end
   EXECUTE FUNCTION _heroku.validate_extension();


ALTER EVENT TRIGGER validate_extension OWNER TO "user";

--
-- PostgreSQL database dump complete
--

\unrestrict 2IGNQJsOsYxTWJ44zZpLWQ4GDxlJaNt8Lt5AzXJm7LXy2ri7ynspZRGYMxgs9rU

