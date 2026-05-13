--
-- PostgreSQL database dump
--

\restrict Zj0lgLt3mYMnwwYAx3UlBHEhYGfYOJ7sXBZVQiFoVvgK6IgXR2lhD0hTSPEPXZc

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: can_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.can_specs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    part_id uuid NOT NULL,
    can_fd_support boolean DEFAULT false,
    max_baudrate_mbps numeric(4,2),
    vcc_min_v numeric(5,2),
    vcc_max_v numeric(5,2),
    has_isolation boolean DEFAULT false,
    package character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: conflicts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conflicts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_id uuid NOT NULL,
    field_path character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'open'::character varying NOT NULL,
    resolution text,
    resolved_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN conflicts.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.conflicts.status IS 'open, resolved, ignored';


--
-- Name: datasheet_parameters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.datasheet_parameters (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    part_id uuid NOT NULL,
    section character varying(100) NOT NULL,
    parameter character varying(255) NOT NULL,
    min_value text,
    typ_value text,
    max_value text,
    unit character varying(50),
    conditions text,
    source_page integer,
    raw_text text,
    confidence real DEFAULT 1.0,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dcdc_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dcdc_specs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    part_id uuid NOT NULL,
    topology character varying(50),
    is_synchronous boolean DEFAULT false,
    num_outputs integer DEFAULT 1,
    vin_min_v numeric(6,2),
    vin_max_v numeric(6,2),
    vout_min_v numeric(6,2),
    vout_max_v numeric(6,2),
    vout_fixed boolean DEFAULT false,
    iout_max_a numeric(6,3),
    frequency_khz_min integer,
    frequency_khz_max integer,
    efficiency_percent_typ numeric(5,2),
    iq_ua numeric(8,2),
    has_enable boolean,
    has_soft_start boolean,
    has_power_good boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    source_url text NOT NULL,
    source_type character varying(50) NOT NULL,
    doc_hash character varying(64) NOT NULL,
    content_type character varying(100),
    storage_key text NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    fetched_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN documents.source_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.documents.source_type IS 'mfg_pdf, mfg_html, dist_html, other';


--
-- Name: drc_violations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drc_violations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    design_id uuid,
    rule_id character varying(20) NOT NULL,
    rule_name character varying(200),
    severity character varying(20) DEFAULT 'error'::character varying NOT NULL,
    part_id uuid,
    component character varying(100),
    message text NOT NULL,
    recommendation text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evidence (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_id uuid NOT NULL,
    field_path character varying(255) NOT NULL,
    raw_value text,
    normalized_value jsonb,
    confidence numeric(3,2) DEFAULT 1.0 NOT NULL,
    document_id uuid,
    page_number integer,
    bbox jsonb,
    snippet_image_path text,
    verified boolean DEFAULT false,
    verified_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: extraction_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.extraction_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    parser_version character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    error_message text,
    stats jsonb,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: COLUMN extraction_runs.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.extraction_runs.status IS 'success, partial, failed';


--
-- Name: firmware_stacks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.firmware_stacks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    stack_name character varying(200) NOT NULL,
    stack_type character varying(50) NOT NULL,
    vendor character varying(100),
    version character varying(50),
    license character varying(100),
    flash_typical_kb integer,
    ram_typical_kb integer,
    supported_cores text[],
    features text[],
    protocols text[],
    documentation_url text,
    repository_url text,
    popularity_score integer DEFAULT 50,
    maturity_score integer DEFAULT 50,
    community_score integer DEFAULT 50,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: ldo_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ldo_specs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    part_id uuid NOT NULL,
    vin_min_v numeric(5,2),
    vin_max_v numeric(5,2),
    vout_fixed_v numeric(5,2),
    vout_adj_min_v numeric(5,2),
    vout_adj_max_v numeric(5,2),
    iout_max_ma numeric(8,2),
    dropout_mv numeric(6,2),
    quiescent_ua numeric(8,2),
    package character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: mcu_pin_functions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcu_pin_functions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_id uuid,
    pin_number integer NOT NULL,
    pin_name character varying(50) NOT NULL,
    af0_function character varying(100),
    af1_function character varying(100),
    af2_function character varying(100),
    af3_function character varying(100),
    af4_function character varying(100),
    af5_function character varying(100),
    af6_function character varying(100),
    af7_function character varying(100),
    af8_function character varying(100),
    af9_function character varying(100),
    af10_function character varying(100),
    af11_function character varying(100),
    af12_function character varying(100),
    af13_function character varying(100),
    af14_function character varying(100),
    af15_function character varying(100),
    max_current_ma integer,
    voltage_tolerance character varying(50),
    is_power_pin boolean DEFAULT false,
    is_boot_pin boolean DEFAULT false,
    has_adc boolean DEFAULT false,
    has_dac boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE mcu_pin_functions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.mcu_pin_functions IS 'MCU pin alternate function mappings';


--
-- Name: COLUMN mcu_pin_functions.af0_function; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.mcu_pin_functions.af0_function IS 'Default function (usually GPIO)';


--
-- Name: mcu_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcu_specs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    part_id uuid NOT NULL,
    core character varying(100),
    max_mhz integer,
    flash_kb integer,
    sram_kb integer,
    ram_kb integer,
    eeprom_kb integer,
    can_count integer DEFAULT 0,
    can_fd_count integer DEFAULT 0,
    usb_fs integer DEFAULT 0,
    usb_hs integer DEFAULT 0,
    usb_count integer DEFAULT 0,
    uart_count integer DEFAULT 0,
    i2c_count integer DEFAULT 0,
    spi_count integer DEFAULT 0,
    adc_channels integer DEFAULT 0,
    adc_count integer DEFAULT 0,
    dac_channels integer DEFAULT 0,
    dac_count integer DEFAULT 0,
    ethernet integer DEFAULT 0,
    ethernet_count integer DEFAULT 0,
    timers_count integer DEFAULT 0,
    timer_count integer DEFAULT 0,
    pwm_channels integer DEFAULT 0,
    has_fpu integer DEFAULT 0,
    has_dsp integer DEFAULT 0,
    has_crypto integer DEFAULT 0,
    has_wireless integer DEFAULT 0,
    vdd_min_v numeric(4,2),
    vdd_max_v numeric(4,2),
    voltage_min_v numeric(4,2),
    voltage_max_v numeric(4,2),
    active_ma numeric(8,2),
    standby_ua numeric(8,2),
    sleep_ua numeric(8,2),
    cost_usd numeric(8,2),
    extras jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: parts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    mpn character varying(100) NOT NULL,
    manufacturer character varying(100) NOT NULL,
    family character varying(100),
    description text,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    package_family character varying(50),
    package_name character varying(100),
    pin_count integer,
    theta_ja_c_w real,
    temp_min_c integer,
    temp_max_c integer,
    datasheet_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN parts.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parts.status IS 'active, nrnd, eol, unknown';


--
-- Name: parts_needing_review; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.parts_needing_review AS
 SELECT DISTINCT p.id,
    p.mpn,
    p.manufacturer,
    'low_confidence'::text AS reason,
    min(e.confidence) AS min_confidence
   FROM (public.parts p
     JOIN public.evidence e ON ((p.id = e.part_id)))
  WHERE (e.confidence < 0.85)
  GROUP BY p.id, p.mpn, p.manufacturer
UNION
 SELECT DISTINCT p.id,
    p.mpn,
    p.manufacturer,
    'conflict'::text AS reason,
    NULL::numeric AS min_confidence
   FROM (public.parts p
     JOIN public.conflicts c ON ((p.id = c.part_id)))
  WHERE ((c.status)::text = 'open'::text);


--
-- Name: parts_with_specs; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.parts_with_specs AS
SELECT
    NULL::uuid AS id,
    NULL::character varying(100) AS mpn,
    NULL::character varying(100) AS manufacturer,
    NULL::character varying(100) AS family,
    NULL::text AS description,
    NULL::character varying(50) AS status,
    NULL::character varying(50) AS package_family,
    NULL::character varying(100) AS package_name,
    NULL::integer AS pin_count,
    NULL::real AS theta_ja_c_w,
    NULL::integer AS temp_min_c,
    NULL::integer AS temp_max_c,
    NULL::text AS datasheet_url,
    NULL::timestamp with time zone AS created_at,
    NULL::timestamp with time zone AS updated_at,
    NULL::character varying(100) AS core,
    NULL::integer AS max_mhz,
    NULL::integer AS flash_kb,
    NULL::integer AS sram_kb,
    NULL::integer AS can_count,
    NULL::numeric(8,2) AS cost_usd,
    NULL::bigint AS evidence_count;


--
-- Name: passive_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passive_specs (
    part_id uuid NOT NULL,
    type character varying(50) NOT NULL,
    value_primary numeric(15,6),
    tolerance_percent numeric(5,2),
    power_rating_w numeric(6,3),
    voltage_rating_v numeric(6,2),
    package_case character varying(50),
    dielectric_type character varying(50)
);


--
-- Name: peripheral_power; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.peripheral_power (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_id uuid,
    peripheral_type character varying(50) NOT NULL,
    peripheral_instance character varying(50),
    current_typ_ua numeric(12,2),
    current_max_ua numeric(12,2),
    operating_frequency_mhz numeric(10,2),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE peripheral_power; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.peripheral_power IS 'Peripheral power consumption data';


--
-- Name: pin_mux_constraints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pin_mux_constraints (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_id uuid,
    constraint_type character varying(50) NOT NULL,
    pin_names text[] NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE pin_mux_constraints; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.pin_mux_constraints IS 'Pin muxing constraints (exclusive groups, required pairs, etc.)';


--
-- Name: COLUMN pin_mux_constraints.constraint_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pin_mux_constraints.constraint_type IS 'Type: exclusive, required_pair, voltage_level, etc.';


--
-- Name: pinned_parts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pinned_parts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    session_id uuid,
    part_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pmic_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pmic_specs (
    part_id uuid NOT NULL,
    input_voltage_min_v numeric(5,2),
    input_voltage_max_v numeric(5,2),
    output_count integer,
    buck_count integer DEFAULT 0,
    ldo_count integer DEFAULT 0,
    boost_count integer DEFAULT 0,
    control_interface text[],
    automotive_grade boolean DEFAULT false,
    operating_temp_min_c integer,
    operating_temp_max_c integer,
    package_type text
);


--
-- Name: power_modes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.power_modes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_id uuid,
    mode_name character varying(50) NOT NULL,
    voltage_v numeric(4,2) NOT NULL,
    current_typ_ua numeric(12,2),
    current_max_ua numeric(12,2),
    frequency_mhz numeric(10,2),
    temperature_c integer,
    peripherals_active text[],
    notes text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE power_modes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.power_modes IS 'MCU power consumption in different operating modes';


--
-- Name: COLUMN power_modes.current_typ_ua; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.power_modes.current_typ_ua IS 'Typical current consumption in microamps';


--
-- Name: COLUMN power_modes.peripherals_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.power_modes.peripherals_active IS 'List of peripherals active in this mode';


--
-- Name: question_turns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.question_turns (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    spec_id uuid,
    turn_index integer NOT NULL,
    question_text text,
    user_answer text,
    parsed_answer jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: recommendation_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recommendation_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    spec_id uuid,
    candidates_count integer,
    top_candidate_id uuid,
    latency_ms integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: reference_designs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reference_designs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    design_name character varying(200) NOT NULL,
    design_code character varying(100) NOT NULL,
    manufacturer character varying(100) NOT NULL,
    application_area character varying(100),
    description text,
    mcu_part_ids uuid[],
    required_peripherals text[],
    schematic_url text,
    bom_url text,
    gerber_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: requirement_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requirement_specs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_text text,
    spec jsonb,
    mode character varying(50) DEFAULT 'discovery'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sensor_specs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sensor_specs (
    part_id uuid NOT NULL,
    sensor_type character varying(50) NOT NULL,
    interface text[],
    supply_voltage_min_v numeric(4,2),
    supply_voltage_max_v numeric(4,2),
    resolution_bits integer,
    sampling_rate_hz numeric(10,2),
    package_type text,
    automotive_grade boolean DEFAULT false
);


--
-- Name: templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    subsystems jsonb NOT NULL,
    questions jsonb NOT NULL,
    mapping_rules jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_selections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_selections (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    session_id uuid,
    query_text text NOT NULL,
    query_type character varying(50) DEFAULT 'search'::character varying,
    results_shown uuid[],
    result_count integer,
    selected_part_id uuid,
    selection_rank integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    session_key character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_active_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: can_specs can_specs_part_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.can_specs
    ADD CONSTRAINT can_specs_part_id_key UNIQUE (part_id);


--
-- Name: can_specs can_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.can_specs
    ADD CONSTRAINT can_specs_pkey PRIMARY KEY (id);


--
-- Name: conflicts conflicts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conflicts
    ADD CONSTRAINT conflicts_pkey PRIMARY KEY (id);


--
-- Name: datasheet_parameters datasheet_parameters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasheet_parameters
    ADD CONSTRAINT datasheet_parameters_pkey PRIMARY KEY (id);


--
-- Name: dcdc_specs dcdc_specs_part_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dcdc_specs
    ADD CONSTRAINT dcdc_specs_part_id_key UNIQUE (part_id);


--
-- Name: dcdc_specs dcdc_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dcdc_specs
    ADD CONSTRAINT dcdc_specs_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: documents documents_source_url_doc_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_source_url_doc_hash_key UNIQUE (source_url, doc_hash);


--
-- Name: drc_violations drc_violations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drc_violations
    ADD CONSTRAINT drc_violations_pkey PRIMARY KEY (id);


--
-- Name: evidence evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_pkey PRIMARY KEY (id);


--
-- Name: extraction_runs extraction_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_runs
    ADD CONSTRAINT extraction_runs_pkey PRIMARY KEY (id);


--
-- Name: firmware_stacks firmware_stacks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.firmware_stacks
    ADD CONSTRAINT firmware_stacks_pkey PRIMARY KEY (id);


--
-- Name: firmware_stacks firmware_stacks_stack_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.firmware_stacks
    ADD CONSTRAINT firmware_stacks_stack_name_key UNIQUE (stack_name);


--
-- Name: ldo_specs ldo_specs_part_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ldo_specs
    ADD CONSTRAINT ldo_specs_part_id_key UNIQUE (part_id);


--
-- Name: ldo_specs ldo_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ldo_specs
    ADD CONSTRAINT ldo_specs_pkey PRIMARY KEY (id);


--
-- Name: mcu_pin_functions mcu_pin_functions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcu_pin_functions
    ADD CONSTRAINT mcu_pin_functions_pkey PRIMARY KEY (id);


--
-- Name: mcu_specs mcu_specs_part_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcu_specs
    ADD CONSTRAINT mcu_specs_part_id_key UNIQUE (part_id);


--
-- Name: mcu_specs mcu_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcu_specs
    ADD CONSTRAINT mcu_specs_pkey PRIMARY KEY (id);


--
-- Name: parts parts_mpn_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parts
    ADD CONSTRAINT parts_mpn_key UNIQUE (mpn);


--
-- Name: parts parts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parts
    ADD CONSTRAINT parts_pkey PRIMARY KEY (id);


--
-- Name: passive_specs passive_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passive_specs
    ADD CONSTRAINT passive_specs_pkey PRIMARY KEY (part_id);


--
-- Name: peripheral_power peripheral_power_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peripheral_power
    ADD CONSTRAINT peripheral_power_pkey PRIMARY KEY (id);


--
-- Name: pin_mux_constraints pin_mux_constraints_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pin_mux_constraints
    ADD CONSTRAINT pin_mux_constraints_pkey PRIMARY KEY (id);


--
-- Name: pinned_parts pinned_parts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pinned_parts
    ADD CONSTRAINT pinned_parts_pkey PRIMARY KEY (id);


--
-- Name: pinned_parts pinned_parts_session_id_part_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pinned_parts
    ADD CONSTRAINT pinned_parts_session_id_part_id_key UNIQUE (session_id, part_id);


--
-- Name: pmic_specs pmic_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pmic_specs
    ADD CONSTRAINT pmic_specs_pkey PRIMARY KEY (part_id);


--
-- Name: power_modes power_modes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.power_modes
    ADD CONSTRAINT power_modes_pkey PRIMARY KEY (id);


--
-- Name: question_turns question_turns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_turns
    ADD CONSTRAINT question_turns_pkey PRIMARY KEY (id);


--
-- Name: recommendation_logs recommendation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recommendation_logs
    ADD CONSTRAINT recommendation_logs_pkey PRIMARY KEY (id);


--
-- Name: reference_designs reference_designs_design_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reference_designs
    ADD CONSTRAINT reference_designs_design_code_key UNIQUE (design_code);


--
-- Name: reference_designs reference_designs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reference_designs
    ADD CONSTRAINT reference_designs_pkey PRIMARY KEY (id);


--
-- Name: requirement_specs requirement_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requirement_specs
    ADD CONSTRAINT requirement_specs_pkey PRIMARY KEY (id);


--
-- Name: sensor_specs sensor_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sensor_specs
    ADD CONSTRAINT sensor_specs_pkey PRIMARY KEY (part_id);


--
-- Name: templates templates_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_name_key UNIQUE (name);


--
-- Name: templates templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_pkey PRIMARY KEY (id);


--
-- Name: user_selections user_selections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_selections
    ADD CONSTRAINT user_selections_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_session_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_session_key_key UNIQUE (session_key);


--
-- Name: idx_can_specs_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_can_specs_part ON public.can_specs USING btree (part_id);


--
-- Name: idx_conflicts_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conflicts_part ON public.conflicts USING btree (part_id);


--
-- Name: idx_conflicts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conflicts_status ON public.conflicts USING btree (status);


--
-- Name: idx_dcdc_iout; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dcdc_iout ON public.dcdc_specs USING btree (iout_max_a);


--
-- Name: idx_dcdc_specs_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dcdc_specs_part ON public.dcdc_specs USING btree (part_id);


--
-- Name: idx_dcdc_topology; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dcdc_topology ON public.dcdc_specs USING btree (topology);


--
-- Name: idx_dcdc_vin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dcdc_vin ON public.dcdc_specs USING btree (vin_min_v, vin_max_v);


--
-- Name: idx_dcdc_vout; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dcdc_vout ON public.dcdc_specs USING btree (vout_min_v, vout_max_v);


--
-- Name: idx_documents_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_hash ON public.documents USING btree (doc_hash);


--
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_type ON public.documents USING btree (source_type);


--
-- Name: idx_documents_url; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_url ON public.documents USING btree (source_url);


--
-- Name: idx_drc_violations_design; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_drc_violations_design ON public.drc_violations USING btree (design_id);


--
-- Name: idx_drc_violations_rule; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_drc_violations_rule ON public.drc_violations USING btree (rule_id);


--
-- Name: idx_drc_violations_sev; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_drc_violations_sev ON public.drc_violations USING btree (severity);


--
-- Name: idx_ds_params_param; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ds_params_param ON public.datasheet_parameters USING btree (parameter);


--
-- Name: idx_ds_params_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ds_params_part ON public.datasheet_parameters USING btree (part_id);


--
-- Name: idx_ds_params_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ds_params_section ON public.datasheet_parameters USING btree (part_id, section);


--
-- Name: idx_evidence_confidence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evidence_confidence ON public.evidence USING btree (confidence);


--
-- Name: idx_evidence_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evidence_document ON public.evidence USING btree (document_id);


--
-- Name: idx_evidence_field; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evidence_field ON public.evidence USING btree (part_id, field_path);


--
-- Name: idx_evidence_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evidence_part ON public.evidence USING btree (part_id);


--
-- Name: idx_extraction_runs_document; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_runs_document ON public.extraction_runs USING btree (document_id);


--
-- Name: idx_extraction_runs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_extraction_runs_status ON public.extraction_runs USING btree (status);


--
-- Name: idx_firmware_stacks_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_firmware_stacks_type ON public.firmware_stacks USING btree (stack_type);


--
-- Name: idx_ldo_specs_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ldo_specs_part ON public.ldo_specs USING btree (part_id);


--
-- Name: idx_mcu_specs_can; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcu_specs_can ON public.mcu_specs USING btree (can_count);


--
-- Name: idx_mcu_specs_composite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcu_specs_composite ON public.mcu_specs USING btree (core, flash_kb, sram_kb);


--
-- Name: idx_mcu_specs_core; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcu_specs_core ON public.mcu_specs USING btree (core);


--
-- Name: idx_mcu_specs_flash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcu_specs_flash ON public.mcu_specs USING btree (flash_kb);


--
-- Name: idx_mcu_specs_peripherals; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcu_specs_peripherals ON public.mcu_specs USING btree (uart_count, spi_count, i2c_count);


--
-- Name: idx_mcu_specs_sram; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mcu_specs_sram ON public.mcu_specs USING btree (sram_kb);


--
-- Name: idx_parts_composite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parts_composite ON public.parts USING btree (manufacturer, status, package_family);


--
-- Name: idx_parts_manufacturer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parts_manufacturer ON public.parts USING btree (manufacturer);


--
-- Name: idx_parts_package_family; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parts_package_family ON public.parts USING btree (package_family);


--
-- Name: idx_parts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parts_status ON public.parts USING btree (status);


--
-- Name: idx_parts_temp_range; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parts_temp_range ON public.parts USING btree (temp_min_c, temp_max_c);


--
-- Name: idx_passive_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_passive_package ON public.passive_specs USING btree (package_case);


--
-- Name: idx_passive_specs_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_passive_specs_part ON public.passive_specs USING btree (part_id);


--
-- Name: idx_passive_type_val; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_passive_type_val ON public.passive_specs USING btree (type, value_primary);


--
-- Name: idx_peripheral_power_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_peripheral_power_part ON public.peripheral_power USING btree (part_id);


--
-- Name: idx_peripheral_power_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_peripheral_power_type ON public.peripheral_power USING btree (peripheral_type);


--
-- Name: idx_pin_constraints_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pin_constraints_part ON public.pin_mux_constraints USING btree (part_id);


--
-- Name: idx_pin_functions_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pin_functions_name ON public.mcu_pin_functions USING btree (pin_name);


--
-- Name: idx_pin_functions_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pin_functions_part ON public.mcu_pin_functions USING btree (part_id);


--
-- Name: idx_pmic_input_v; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pmic_input_v ON public.pmic_specs USING btree (input_voltage_min_v, input_voltage_max_v);


--
-- Name: idx_pmic_out_count; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pmic_out_count ON public.pmic_specs USING btree (output_count);


--
-- Name: idx_pmic_specs_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pmic_specs_part ON public.pmic_specs USING btree (part_id);


--
-- Name: idx_power_modes_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_power_modes_mode ON public.power_modes USING btree (mode_name);


--
-- Name: idx_power_modes_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_power_modes_part ON public.power_modes USING btree (part_id);


--
-- Name: idx_question_turns_spec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_question_turns_spec ON public.question_turns USING btree (spec_id);


--
-- Name: idx_question_turns_turn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_question_turns_turn ON public.question_turns USING btree (spec_id, turn_index);


--
-- Name: idx_recommendation_logs_spec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_recommendation_logs_spec ON public.recommendation_logs USING btree (spec_id);


--
-- Name: idx_ref_designs_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ref_designs_app ON public.reference_designs USING btree (application_area);


--
-- Name: idx_ref_designs_mfr; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ref_designs_mfr ON public.reference_designs USING btree (manufacturer);


--
-- Name: idx_requirement_specs_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_requirement_specs_mode ON public.requirement_specs USING btree (mode);


--
-- Name: idx_sensor_interface; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sensor_interface ON public.sensor_specs USING gin (interface);


--
-- Name: idx_sensor_specs_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sensor_specs_part ON public.sensor_specs USING btree (part_id);


--
-- Name: idx_sensor_specs_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sensor_specs_type ON public.sensor_specs USING btree (sensor_type);


--
-- Name: idx_sensor_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sensor_type ON public.sensor_specs USING btree (sensor_type);


--
-- Name: idx_templates_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_templates_name ON public.templates USING btree (name);


--
-- Name: idx_user_selections_part; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_selections_part ON public.user_selections USING btree (selected_part_id);


--
-- Name: idx_user_selections_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_selections_session ON public.user_selections USING btree (session_id);


--
-- Name: parts_with_specs _RETURN; Type: RULE; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.parts_with_specs AS
 SELECT p.id,
    p.mpn,
    p.manufacturer,
    p.family,
    p.description,
    p.status,
    p.package_family,
    p.package_name,
    p.pin_count,
    p.theta_ja_c_w,
    p.temp_min_c,
    p.temp_max_c,
    p.datasheet_url,
    p.created_at,
    p.updated_at,
    m.core,
    m.max_mhz,
    m.flash_kb,
    m.sram_kb,
    m.can_count,
    m.cost_usd,
    count(DISTINCT e.id) AS evidence_count
   FROM ((public.parts p
     LEFT JOIN public.mcu_specs m ON ((p.id = m.part_id)))
     LEFT JOIN public.evidence e ON ((p.id = e.part_id)))
  GROUP BY p.id, m.id;


--
-- Name: dcdc_specs update_dcdc_specs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_dcdc_specs_updated_at BEFORE UPDATE ON public.dcdc_specs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: mcu_specs update_mcu_specs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_mcu_specs_updated_at BEFORE UPDATE ON public.mcu_specs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: parts update_parts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_parts_updated_at BEFORE UPDATE ON public.parts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: requirement_specs update_requirement_specs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_requirement_specs_updated_at BEFORE UPDATE ON public.requirement_specs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: templates update_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON public.templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: can_specs can_specs_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.can_specs
    ADD CONSTRAINT can_specs_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: conflicts conflicts_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conflicts
    ADD CONSTRAINT conflicts_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: datasheet_parameters datasheet_parameters_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.datasheet_parameters
    ADD CONSTRAINT datasheet_parameters_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: drc_violations drc_violations_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drc_violations
    ADD CONSTRAINT drc_violations_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE SET NULL;


--
-- Name: evidence evidence_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: evidence evidence_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: extraction_runs extraction_runs_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.extraction_runs
    ADD CONSTRAINT extraction_runs_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: ldo_specs ldo_specs_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ldo_specs
    ADD CONSTRAINT ldo_specs_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: mcu_specs mcu_specs_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcu_specs
    ADD CONSTRAINT mcu_specs_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: pinned_parts pinned_parts_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pinned_parts
    ADD CONSTRAINT pinned_parts_part_id_fkey FOREIGN KEY (part_id) REFERENCES public.parts(id) ON DELETE CASCADE;


--
-- Name: pinned_parts pinned_parts_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pinned_parts
    ADD CONSTRAINT pinned_parts_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.user_sessions(id) ON DELETE CASCADE;


--
-- Name: question_turns question_turns_spec_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question_turns
    ADD CONSTRAINT question_turns_spec_id_fkey FOREIGN KEY (spec_id) REFERENCES public.requirement_specs(id) ON DELETE CASCADE;


--
-- Name: recommendation_logs recommendation_logs_spec_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recommendation_logs
    ADD CONSTRAINT recommendation_logs_spec_id_fkey FOREIGN KEY (spec_id) REFERENCES public.requirement_specs(id) ON DELETE SET NULL;


--
-- Name: user_selections user_selections_selected_part_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_selections
    ADD CONSTRAINT user_selections_selected_part_id_fkey FOREIGN KEY (selected_part_id) REFERENCES public.parts(id) ON DELETE SET NULL;


--
-- Name: user_selections user_selections_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_selections
    ADD CONSTRAINT user_selections_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.user_sessions(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict Zj0lgLt3mYMnwwYAx3UlBHEhYGfYOJ7sXBZVQiFoVvgK6IgXR2lhD0hTSPEPXZc

