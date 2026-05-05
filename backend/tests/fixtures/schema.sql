--
-- PostgreSQL database dump
--

-- Dumped from database version 15.17 (Debian 15.17-1.pgdg13+1)
-- Dumped by pg_dump version 15.17 (Debian 15.17-1.pgdg13+1)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ability; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ability (
    id integer NOT NULL,
    name_en character varying(100) NOT NULL,
    name_fr character varying(100),
    description_en text,
    description_fr text
);


--
-- Name: ability_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ability_id_seq OWNED BY public.ability.id;


--
-- Name: creator; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.creator (
    id integer NOT NULL,
    name character varying(200) NOT NULL
);


--
-- Name: creator_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.creator_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: creator_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.creator_id_seq OWNED BY public.creator.id;


--
-- Name: fusion_sprite; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fusion_sprite (
    id integer NOT NULL,
    head_id integer NOT NULL,
    body_id integer NOT NULL,
    sprite_path text NOT NULL,
    is_custom boolean DEFAULT false NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    source character varying(20) DEFAULT 'local'::character varying NOT NULL,
    CONSTRAINT fusion_sprite_source_check CHECK (((source)::text = ANY ((ARRAY['local'::character varying, 'community'::character varying, 'auto_generated'::character varying])::text[])))
);


--
-- Name: fusion_sprite_creator; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fusion_sprite_creator (
    fusion_sprite_id integer NOT NULL,
    creator_id integer NOT NULL
);


--
-- Name: fusion_sprite_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.fusion_sprite_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fusion_sprite_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.fusion_sprite_id_seq OWNED BY public.fusion_sprite.id;


--
-- Name: generation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.generation (
    id integer NOT NULL,
    name_en character varying(30) NOT NULL,
    name_fr character varying(30) NOT NULL
);


--
-- Name: generation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.generation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: generation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.generation_id_seq OWNED BY public.generation.id;


--
-- Name: item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item (
    id integer NOT NULL,
    name_en character varying(100) NOT NULL,
    name_fr character varying(100),
    category character varying(20) NOT NULL,
    effect text,
    price_buy integer,
    price_sell integer,
    CONSTRAINT item_category_check CHECK (((category)::text = ANY ((ARRAY['fusion'::character varying, 'evolution'::character varying, 'valuable'::character varying])::text[])))
);


--
-- Name: item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.item_id_seq OWNED BY public.item.id;


--
-- Name: location; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.location (
    id integer NOT NULL,
    name_en character varying(200) NOT NULL,
    name_fr character varying(200),
    region character varying(50)
);


--
-- Name: location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.location_id_seq OWNED BY public.location.id;


--
-- Name: move; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.move (
    id integer NOT NULL,
    name_en character varying(100) NOT NULL,
    name_fr character varying(100),
    type_id integer NOT NULL,
    category character varying(10) NOT NULL,
    power integer,
    accuracy integer,
    pp integer NOT NULL,
    description_en text,
    description_fr text,
    source character varying(20) DEFAULT 'base'::character varying NOT NULL,
    CONSTRAINT move_category_check CHECK (((category)::text = ANY ((ARRAY['Physical'::character varying, 'Special'::character varying, 'Status'::character varying])::text[]))),
    CONSTRAINT move_source_check CHECK (((source)::text = ANY ((ARRAY['base'::character varying, 'infinite_fusion'::character varying])::text[])))
);


--
-- Name: move_expert_move; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.move_expert_move (
    id integer NOT NULL,
    move_id integer NOT NULL,
    expert_location character varying(20) NOT NULL,
    required_pokemon_ids integer[] DEFAULT '{}'::integer[] NOT NULL,
    required_type_ids integer[] DEFAULT '{}'::integer[] NOT NULL,
    required_move_ids integer[] DEFAULT '{}'::integer[] NOT NULL,
    CONSTRAINT move_expert_move_expert_location_check CHECK (((expert_location)::text = ANY ((ARRAY['knot_island'::character varying, 'boon_island'::character varying])::text[])))
);


--
-- Name: move_expert_move_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.move_expert_move_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: move_expert_move_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.move_expert_move_id_seq OWNED BY public.move_expert_move.id;


--
-- Name: move_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.move_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: move_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.move_id_seq OWNED BY public.move.id;


--
-- Name: move_tutor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.move_tutor (
    id integer NOT NULL,
    move_id integer NOT NULL,
    location_id integer NOT NULL,
    price integer,
    currency character varying(20) NOT NULL,
    npc_description text,
    CONSTRAINT move_tutor_currency_check CHECK (((currency)::text = ANY ((ARRAY['pokedollars'::character varying, 'free'::character varying, 'quest'::character varying])::text[])))
);


--
-- Name: move_tutor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.move_tutor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: move_tutor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.move_tutor_id_seq OWNED BY public.move_tutor.id;


--
-- Name: pokemon; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon (
    id integer NOT NULL,
    national_id integer,
    name_en character varying(100) NOT NULL,
    name_fr character varying(100),
    generation_id integer NOT NULL,
    hp integer NOT NULL,
    attack integer NOT NULL,
    defense integer NOT NULL,
    sp_attack integer NOT NULL,
    sp_defense integer NOT NULL,
    speed integer NOT NULL,
    base_experience integer,
    is_hoenn_only boolean DEFAULT false NOT NULL,
    sprite_path text,
    pokepedia_url text,
    is_legendary boolean DEFAULT false NOT NULL
);


--
-- Name: pokemon_ability; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon_ability (
    pokemon_id integer NOT NULL,
    ability_id integer NOT NULL,
    slot integer NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    if_swapped boolean DEFAULT false NOT NULL,
    if_override boolean DEFAULT false NOT NULL,
    CONSTRAINT pokemon_ability_slot_check CHECK ((slot = ANY (ARRAY[1, 2, 3])))
);


--
-- Name: pokemon_evolution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon_evolution (
    id integer NOT NULL,
    pokemon_id integer NOT NULL,
    evolves_into_id integer NOT NULL,
    trigger_type character varying(20) NOT NULL,
    min_level integer,
    item_name_en character varying(100),
    item_name_fr character varying(100),
    if_override boolean DEFAULT false NOT NULL,
    if_notes text,
    CONSTRAINT pokemon_evolution_trigger_type_check CHECK (((trigger_type)::text = ANY ((ARRAY['level_up'::character varying, 'use_item'::character varying, 'trade'::character varying, 'friendship'::character varying, 'other'::character varying])::text[])))
);


--
-- Name: pokemon_evolution_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pokemon_evolution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pokemon_evolution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pokemon_evolution_id_seq OWNED BY public.pokemon_evolution.id;


--
-- Name: pokemon_location; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon_location (
    id integer NOT NULL,
    pokemon_id integer NOT NULL,
    location_id integer NOT NULL,
    method character varying(20),
    notes text,
    CONSTRAINT pokemon_location_method_check CHECK (((method)::text = ANY ((ARRAY['wild'::character varying, 'gift'::character varying, 'trade'::character varying, 'static'::character varying, 'fishing'::character varying, 'headbutt'::character varying])::text[])))
);


--
-- Name: pokemon_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pokemon_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pokemon_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pokemon_location_id_seq OWNED BY public.pokemon_location.id;


--
-- Name: pokemon_move; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon_move (
    id integer NOT NULL,
    pokemon_id integer NOT NULL,
    move_id integer NOT NULL,
    method character varying(20) NOT NULL,
    level integer,
    source character varying(20) DEFAULT 'base'::character varying NOT NULL,
    CONSTRAINT pokemon_move_method_check CHECK (((method)::text = ANY ((ARRAY['level_up'::character varying, 'tm'::character varying, 'tutor'::character varying, 'breeding'::character varying, 'special'::character varying, 'before_evolution'::character varying])::text[]))),
    CONSTRAINT pokemon_move_source_check CHECK (((source)::text = ANY ((ARRAY['base'::character varying, 'infinite_fusion'::character varying])::text[])))
);


--
-- Name: pokemon_move_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pokemon_move_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pokemon_move_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pokemon_move_id_seq OWNED BY public.pokemon_move.id;


--
-- Name: pokemon_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon_type (
    pokemon_id integer NOT NULL,
    type_id integer NOT NULL,
    slot integer NOT NULL,
    if_override boolean DEFAULT false NOT NULL,
    CONSTRAINT pokemon_type_slot_check CHECK ((slot = ANY (ARRAY[1, 2])))
);


--
-- Name: tm; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tm (
    id integer NOT NULL,
    number integer NOT NULL,
    move_id integer NOT NULL,
    location text
);


--
-- Name: tm_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tm_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tm_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tm_id_seq OWNED BY public.tm.id;


--
-- Name: tm_location; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tm_location (
    id integer NOT NULL,
    tm_id integer NOT NULL,
    location_id integer NOT NULL,
    notes text
);


--
-- Name: tm_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tm_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tm_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tm_location_id_seq OWNED BY public.tm_location.id;


--
-- Name: triple_fusion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.triple_fusion (
    id integer NOT NULL,
    name_en character varying(100) NOT NULL,
    name_fr character varying(100),
    hp integer NOT NULL,
    attack integer NOT NULL,
    defense integer NOT NULL,
    sp_attack integer NOT NULL,
    sp_defense integer NOT NULL,
    speed integer NOT NULL,
    evolves_from_id integer,
    evolution_level integer,
    steps_to_hatch integer,
    sprite_path text
);


--
-- Name: triple_fusion_ability; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.triple_fusion_ability (
    triple_fusion_id integer NOT NULL,
    ability_id integer NOT NULL,
    slot integer NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    CONSTRAINT triple_fusion_ability_slot_check CHECK ((slot = ANY (ARRAY[1, 2, 3])))
);


--
-- Name: triple_fusion_component; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.triple_fusion_component (
    triple_fusion_id integer NOT NULL,
    pokemon_id integer NOT NULL,
    "position" integer NOT NULL,
    CONSTRAINT triple_fusion_component_position_check CHECK (("position" = ANY (ARRAY[1, 2, 3])))
);


--
-- Name: triple_fusion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.triple_fusion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: triple_fusion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.triple_fusion_id_seq OWNED BY public.triple_fusion.id;


--
-- Name: triple_fusion_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.triple_fusion_type (
    triple_fusion_id integer NOT NULL,
    type_id integer NOT NULL,
    slot integer NOT NULL,
    CONSTRAINT triple_fusion_type_slot_check CHECK (((slot >= 1) AND (slot <= 4)))
);


--
-- Name: type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.type (
    id integer NOT NULL,
    name_en character varying(30) NOT NULL,
    name_fr character varying(30),
    is_triple_fusion_type boolean DEFAULT false NOT NULL
);


--
-- Name: type_effectiveness; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.type_effectiveness (
    attacking_type_id integer NOT NULL,
    defending_type_id integer NOT NULL,
    multiplier numeric(3,2) NOT NULL
);


--
-- Name: type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.type_id_seq OWNED BY public.type.id;


--
-- Name: ability id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ability ALTER COLUMN id SET DEFAULT nextval('public.ability_id_seq'::regclass);


--
-- Name: creator id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creator ALTER COLUMN id SET DEFAULT nextval('public.creator_id_seq'::regclass);


--
-- Name: fusion_sprite id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite ALTER COLUMN id SET DEFAULT nextval('public.fusion_sprite_id_seq'::regclass);


--
-- Name: generation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generation ALTER COLUMN id SET DEFAULT nextval('public.generation_id_seq'::regclass);


--
-- Name: item id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item ALTER COLUMN id SET DEFAULT nextval('public.item_id_seq'::regclass);


--
-- Name: location id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location ALTER COLUMN id SET DEFAULT nextval('public.location_id_seq'::regclass);


--
-- Name: move id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move ALTER COLUMN id SET DEFAULT nextval('public.move_id_seq'::regclass);


--
-- Name: move_expert_move id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_expert_move ALTER COLUMN id SET DEFAULT nextval('public.move_expert_move_id_seq'::regclass);


--
-- Name: move_tutor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_tutor ALTER COLUMN id SET DEFAULT nextval('public.move_tutor_id_seq'::regclass);


--
-- Name: pokemon_evolution id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_evolution ALTER COLUMN id SET DEFAULT nextval('public.pokemon_evolution_id_seq'::regclass);


--
-- Name: pokemon_location id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_location ALTER COLUMN id SET DEFAULT nextval('public.pokemon_location_id_seq'::regclass);


--
-- Name: pokemon_move id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_move ALTER COLUMN id SET DEFAULT nextval('public.pokemon_move_id_seq'::regclass);


--
-- Name: tm id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm ALTER COLUMN id SET DEFAULT nextval('public.tm_id_seq'::regclass);


--
-- Name: tm_location id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm_location ALTER COLUMN id SET DEFAULT nextval('public.tm_location_id_seq'::regclass);


--
-- Name: triple_fusion id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion ALTER COLUMN id SET DEFAULT nextval('public.triple_fusion_id_seq'::regclass);


--
-- Name: type id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.type ALTER COLUMN id SET DEFAULT nextval('public.type_id_seq'::regclass);


--
-- Name: ability ability_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ability
    ADD CONSTRAINT ability_name_en_key UNIQUE (name_en);


--
-- Name: ability ability_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ability
    ADD CONSTRAINT ability_pkey PRIMARY KEY (id);


--
-- Name: creator creator_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creator
    ADD CONSTRAINT creator_name_key UNIQUE (name);


--
-- Name: creator creator_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creator
    ADD CONSTRAINT creator_pkey PRIMARY KEY (id);


--
-- Name: fusion_sprite_creator fusion_sprite_creator_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite_creator
    ADD CONSTRAINT fusion_sprite_creator_pkey PRIMARY KEY (fusion_sprite_id, creator_id);


--
-- Name: fusion_sprite fusion_sprite_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite
    ADD CONSTRAINT fusion_sprite_pkey PRIMARY KEY (id);


--
-- Name: generation generation_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generation
    ADD CONSTRAINT generation_name_en_key UNIQUE (name_en);


--
-- Name: generation generation_name_fr_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generation
    ADD CONSTRAINT generation_name_fr_key UNIQUE (name_fr);


--
-- Name: generation generation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.generation
    ADD CONSTRAINT generation_pkey PRIMARY KEY (id);


--
-- Name: item item_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item
    ADD CONSTRAINT item_name_en_key UNIQUE (name_en);


--
-- Name: item item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item
    ADD CONSTRAINT item_pkey PRIMARY KEY (id);


--
-- Name: location location_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_name_en_key UNIQUE (name_en);


--
-- Name: location location_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_pkey PRIMARY KEY (id);


--
-- Name: move_expert_move move_expert_move_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_expert_move
    ADD CONSTRAINT move_expert_move_pkey PRIMARY KEY (id);


--
-- Name: move move_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move
    ADD CONSTRAINT move_name_en_key UNIQUE (name_en);


--
-- Name: move move_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move
    ADD CONSTRAINT move_pkey PRIMARY KEY (id);


--
-- Name: move_tutor move_tutor_move_id_location_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_tutor
    ADD CONSTRAINT move_tutor_move_id_location_id_key UNIQUE (move_id, location_id);


--
-- Name: move_tutor move_tutor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_tutor
    ADD CONSTRAINT move_tutor_pkey PRIMARY KEY (id);


--
-- Name: pokemon_ability pokemon_ability_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_ability
    ADD CONSTRAINT pokemon_ability_pkey PRIMARY KEY (pokemon_id, slot);


--
-- Name: pokemon_evolution pokemon_evolution_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_evolution
    ADD CONSTRAINT pokemon_evolution_pkey PRIMARY KEY (id);


--
-- Name: pokemon_evolution pokemon_evolution_pokemon_id_evolves_into_id_trigger_type_i_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_evolution
    ADD CONSTRAINT pokemon_evolution_pokemon_id_evolves_into_id_trigger_type_i_key UNIQUE (pokemon_id, evolves_into_id, trigger_type, item_name_en);


--
-- Name: pokemon_location pokemon_location_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_location
    ADD CONSTRAINT pokemon_location_pkey PRIMARY KEY (id);


--
-- Name: pokemon_location pokemon_location_pokemon_id_location_id_method_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_location
    ADD CONSTRAINT pokemon_location_pokemon_id_location_id_method_key UNIQUE (pokemon_id, location_id, method);


--
-- Name: pokemon_move pokemon_move_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_move
    ADD CONSTRAINT pokemon_move_pkey PRIMARY KEY (id);


--
-- Name: pokemon_move pokemon_move_pokemon_id_move_id_method_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_move
    ADD CONSTRAINT pokemon_move_pokemon_id_move_id_method_key UNIQUE (pokemon_id, move_id, method);


--
-- Name: pokemon pokemon_national_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon
    ADD CONSTRAINT pokemon_national_id_key UNIQUE (national_id);


--
-- Name: pokemon pokemon_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon
    ADD CONSTRAINT pokemon_pkey PRIMARY KEY (id);


--
-- Name: pokemon_type pokemon_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_type
    ADD CONSTRAINT pokemon_type_pkey PRIMARY KEY (pokemon_id, slot);


--
-- Name: tm_location tm_location_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm_location
    ADD CONSTRAINT tm_location_pkey PRIMARY KEY (id);


--
-- Name: tm_location tm_location_tm_id_location_id_notes_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm_location
    ADD CONSTRAINT tm_location_tm_id_location_id_notes_key UNIQUE (tm_id, location_id, notes);


--
-- Name: tm tm_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm
    ADD CONSTRAINT tm_number_key UNIQUE (number);


--
-- Name: tm tm_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm
    ADD CONSTRAINT tm_pkey PRIMARY KEY (id);


--
-- Name: triple_fusion_ability triple_fusion_ability_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_ability
    ADD CONSTRAINT triple_fusion_ability_pkey PRIMARY KEY (triple_fusion_id, slot);


--
-- Name: triple_fusion_component triple_fusion_component_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_component
    ADD CONSTRAINT triple_fusion_component_pkey PRIMARY KEY (triple_fusion_id, "position");


--
-- Name: triple_fusion triple_fusion_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion
    ADD CONSTRAINT triple_fusion_name_en_key UNIQUE (name_en);


--
-- Name: triple_fusion triple_fusion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion
    ADD CONSTRAINT triple_fusion_pkey PRIMARY KEY (id);


--
-- Name: triple_fusion_type triple_fusion_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_type
    ADD CONSTRAINT triple_fusion_type_pkey PRIMARY KEY (triple_fusion_id, slot);


--
-- Name: type_effectiveness type_effectiveness_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.type_effectiveness
    ADD CONSTRAINT type_effectiveness_pkey PRIMARY KEY (attacking_type_id, defending_type_id);


--
-- Name: type type_name_en_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.type
    ADD CONSTRAINT type_name_en_key UNIQUE (name_en);


--
-- Name: type type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.type
    ADD CONSTRAINT type_pkey PRIMARY KEY (id);


--
-- Name: idx_evolution_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evolution_from ON public.pokemon_evolution USING btree (pokemon_id);


--
-- Name: idx_evolution_into; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evolution_into ON public.pokemon_evolution USING btree (evolves_into_id);


--
-- Name: idx_evolution_override; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evolution_override ON public.pokemon_evolution USING btree (if_override);


--
-- Name: idx_fusion_creator_sprite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fusion_creator_sprite ON public.fusion_sprite_creator USING btree (fusion_sprite_id);


--
-- Name: idx_fusion_sprite_body; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fusion_sprite_body ON public.fusion_sprite USING btree (body_id);


--
-- Name: idx_fusion_sprite_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fusion_sprite_default ON public.fusion_sprite USING btree (head_id, body_id, is_default);


--
-- Name: idx_fusion_sprite_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fusion_sprite_pair ON public.fusion_sprite USING btree (head_id, body_id);


--
-- Name: idx_item_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_item_category ON public.item USING btree (category);


--
-- Name: idx_location_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_location_region ON public.location USING btree (region);


--
-- Name: idx_move_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_move_category ON public.move USING btree (category);


--
-- Name: idx_move_expert_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_move_expert_location ON public.move_expert_move USING btree (expert_location);


--
-- Name: idx_move_expert_move; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_move_expert_move ON public.move_expert_move USING btree (move_id);


--
-- Name: idx_move_tutor_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_move_tutor_location ON public.move_tutor USING btree (location_id);


--
-- Name: idx_move_tutor_move; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_move_tutor_move ON public.move_tutor USING btree (move_id);


--
-- Name: idx_move_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_move_type ON public.move USING btree (type_id);


--
-- Name: idx_pokemon_ability_ab; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_ability_ab ON public.pokemon_ability USING btree (ability_id);


--
-- Name: idx_pokemon_ability_pok; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_ability_pok ON public.pokemon_ability USING btree (pokemon_id);


--
-- Name: idx_pokemon_generation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_generation ON public.pokemon USING btree (generation_id);


--
-- Name: idx_pokemon_location_pok; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_location_pok ON public.pokemon_location USING btree (pokemon_id);


--
-- Name: idx_pokemon_move_method; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_move_method ON public.pokemon_move USING btree (method);


--
-- Name: idx_pokemon_move_move; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_move_move ON public.pokemon_move USING btree (move_id);


--
-- Name: idx_pokemon_move_pokemon; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_move_pokemon ON public.pokemon_move USING btree (pokemon_id);


--
-- Name: idx_pokemon_name_en; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_name_en ON public.pokemon USING btree (name_en);


--
-- Name: idx_pokemon_name_fr; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_name_fr ON public.pokemon USING btree (name_fr);


--
-- Name: idx_pokemon_national; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_national ON public.pokemon USING btree (national_id);


--
-- Name: idx_pokemon_type_pokemon; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_type_pokemon ON public.pokemon_type USING btree (pokemon_id);


--
-- Name: idx_pokemon_type_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_type_type ON public.pokemon_type USING btree (type_id);


--
-- Name: idx_tf_component_fusion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tf_component_fusion ON public.triple_fusion_component USING btree (triple_fusion_id);


--
-- Name: idx_tf_component_pokemon; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tf_component_pokemon ON public.triple_fusion_component USING btree (pokemon_id);


--
-- Name: idx_tf_evolves_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tf_evolves_from ON public.triple_fusion USING btree (evolves_from_id);


--
-- Name: idx_tf_type_fusion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tf_type_fusion ON public.triple_fusion_type USING btree (triple_fusion_id);


--
-- Name: idx_tm_location_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tm_location_location ON public.tm_location USING btree (location_id);


--
-- Name: idx_tm_location_tm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tm_location_tm ON public.tm_location USING btree (tm_id);


--
-- Name: idx_type_eff_attacking; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_type_eff_attacking ON public.type_effectiveness USING btree (attacking_type_id);


--
-- Name: idx_type_eff_defending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_type_eff_defending ON public.type_effectiveness USING btree (defending_type_id);


--
-- Name: uq_fusion_sprite_default; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fusion_sprite_default ON public.fusion_sprite USING btree (head_id, body_id) WHERE (is_default = true);


--
-- Name: fusion_sprite fusion_sprite_body_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite
    ADD CONSTRAINT fusion_sprite_body_id_fkey FOREIGN KEY (body_id) REFERENCES public.pokemon(id);


--
-- Name: fusion_sprite_creator fusion_sprite_creator_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite_creator
    ADD CONSTRAINT fusion_sprite_creator_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.creator(id);


--
-- Name: fusion_sprite_creator fusion_sprite_creator_fusion_sprite_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite_creator
    ADD CONSTRAINT fusion_sprite_creator_fusion_sprite_id_fkey FOREIGN KEY (fusion_sprite_id) REFERENCES public.fusion_sprite(id) ON DELETE CASCADE;


--
-- Name: fusion_sprite fusion_sprite_head_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fusion_sprite
    ADD CONSTRAINT fusion_sprite_head_id_fkey FOREIGN KEY (head_id) REFERENCES public.pokemon(id);


--
-- Name: move_expert_move move_expert_move_move_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_expert_move
    ADD CONSTRAINT move_expert_move_move_id_fkey FOREIGN KEY (move_id) REFERENCES public.move(id) ON DELETE CASCADE;


--
-- Name: move_tutor move_tutor_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_tutor
    ADD CONSTRAINT move_tutor_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: move_tutor move_tutor_move_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move_tutor
    ADD CONSTRAINT move_tutor_move_id_fkey FOREIGN KEY (move_id) REFERENCES public.move(id) ON DELETE CASCADE;


--
-- Name: move move_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.move
    ADD CONSTRAINT move_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.type(id);


--
-- Name: pokemon_ability pokemon_ability_ability_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_ability
    ADD CONSTRAINT pokemon_ability_ability_id_fkey FOREIGN KEY (ability_id) REFERENCES public.ability(id);


--
-- Name: pokemon_ability pokemon_ability_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_ability
    ADD CONSTRAINT pokemon_ability_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokemon(id) ON DELETE CASCADE;


--
-- Name: pokemon_evolution pokemon_evolution_evolves_into_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_evolution
    ADD CONSTRAINT pokemon_evolution_evolves_into_id_fkey FOREIGN KEY (evolves_into_id) REFERENCES public.pokemon(id);


--
-- Name: pokemon_evolution pokemon_evolution_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_evolution
    ADD CONSTRAINT pokemon_evolution_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokemon(id);


--
-- Name: pokemon pokemon_generation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon
    ADD CONSTRAINT pokemon_generation_id_fkey FOREIGN KEY (generation_id) REFERENCES public.generation(id);


--
-- Name: pokemon_location pokemon_location_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_location
    ADD CONSTRAINT pokemon_location_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: pokemon_location pokemon_location_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_location
    ADD CONSTRAINT pokemon_location_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokemon(id) ON DELETE CASCADE;


--
-- Name: pokemon_move pokemon_move_move_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_move
    ADD CONSTRAINT pokemon_move_move_id_fkey FOREIGN KEY (move_id) REFERENCES public.move(id);


--
-- Name: pokemon_move pokemon_move_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_move
    ADD CONSTRAINT pokemon_move_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokemon(id) ON DELETE CASCADE;


--
-- Name: pokemon_type pokemon_type_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_type
    ADD CONSTRAINT pokemon_type_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokemon(id) ON DELETE CASCADE;


--
-- Name: pokemon_type pokemon_type_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_type
    ADD CONSTRAINT pokemon_type_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.type(id);


--
-- Name: tm_location tm_location_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm_location
    ADD CONSTRAINT tm_location_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id);


--
-- Name: tm_location tm_location_tm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm_location
    ADD CONSTRAINT tm_location_tm_id_fkey FOREIGN KEY (tm_id) REFERENCES public.tm(id) ON DELETE CASCADE;


--
-- Name: tm tm_move_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tm
    ADD CONSTRAINT tm_move_id_fkey FOREIGN KEY (move_id) REFERENCES public.move(id);


--
-- Name: triple_fusion_ability triple_fusion_ability_ability_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_ability
    ADD CONSTRAINT triple_fusion_ability_ability_id_fkey FOREIGN KEY (ability_id) REFERENCES public.ability(id);


--
-- Name: triple_fusion_ability triple_fusion_ability_triple_fusion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_ability
    ADD CONSTRAINT triple_fusion_ability_triple_fusion_id_fkey FOREIGN KEY (triple_fusion_id) REFERENCES public.triple_fusion(id) ON DELETE CASCADE;


--
-- Name: triple_fusion_component triple_fusion_component_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_component
    ADD CONSTRAINT triple_fusion_component_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokemon(id);


--
-- Name: triple_fusion_component triple_fusion_component_triple_fusion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_component
    ADD CONSTRAINT triple_fusion_component_triple_fusion_id_fkey FOREIGN KEY (triple_fusion_id) REFERENCES public.triple_fusion(id) ON DELETE CASCADE;


--
-- Name: triple_fusion triple_fusion_evolves_from_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion
    ADD CONSTRAINT triple_fusion_evolves_from_id_fkey FOREIGN KEY (evolves_from_id) REFERENCES public.triple_fusion(id);


--
-- Name: triple_fusion_type triple_fusion_type_triple_fusion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_type
    ADD CONSTRAINT triple_fusion_type_triple_fusion_id_fkey FOREIGN KEY (triple_fusion_id) REFERENCES public.triple_fusion(id) ON DELETE CASCADE;


--
-- Name: triple_fusion_type triple_fusion_type_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.triple_fusion_type
    ADD CONSTRAINT triple_fusion_type_type_id_fkey FOREIGN KEY (type_id) REFERENCES public.type(id);


--
-- Name: type_effectiveness type_effectiveness_attacking_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.type_effectiveness
    ADD CONSTRAINT type_effectiveness_attacking_type_id_fkey FOREIGN KEY (attacking_type_id) REFERENCES public.type(id) ON DELETE CASCADE;


--
-- Name: type_effectiveness type_effectiveness_defending_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.type_effectiveness
    ADD CONSTRAINT type_effectiveness_defending_type_id_fkey FOREIGN KEY (defending_type_id) REFERENCES public.type(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict y3PGcarii0pU8faMb9Hg7B3NVkEM337him0TGj6ICbSB2Zy88oUdze9r6fUmIMo

