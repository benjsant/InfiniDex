-- Minimal fusion_sprite rows for tests (pairs: 1/1, 1/4, 4/1, 25/6)
COPY fusion_sprite (id, head_id, body_id, sprite_path, is_custom, is_default, source) FROM stdin;
1	1	1	1.1.png	t	t	community
319	1	4	1.4.png	t	t	community
54635	25	6	25.6.png	t	t	community
108458	4	1	4.1.png	t	t	community
\.

COPY fusion_sprite_creator (fusion_sprite_id, creator_id) FROM stdin;
1	6880
319	2062
54635	6436
108458	5248
\.
