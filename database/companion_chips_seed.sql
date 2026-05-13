--
-- PostgreSQL database dump
--

\restrict jciB9LTLrmTic7U3Hz8Ei2hAYUAKNj1VC09slzz5SkIVd5Jkhemjoo9x4FG05R0

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
-- Data for Name: companion_chips; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.companion_chips (id, mpn, manufacturer, category, description, interface, vcc_min_v, vcc_max_v, logic_level_v, datarate_kbps, max_current_a, cost_usd, package, notes, tags, created_at) FROM stdin;
6dc105ba-ca14-4ce2-ac10-f9c8dfa30f65	TCAN1042VDRQ1	Texas Instruments	can_transceiver	Automotive CAN-FD Transceiver, 5Mbps, Fault Protected	CAN	4.50	5.50	3.30	5000	\N	1.85	SOIC-8	Works with 3.3V MCU logic. Automotive grade AEC-Q100. CAN-FD capable.	{can,can-fd,automotive,5v}	2026-05-14 00:01:58.273431+05:30
8d5e898b-2883-4f5b-ab1c-fca44967e8f7	SN65HVD230DR	Texas Instruments	can_transceiver	CAN Bus Transceiver, 3.3V, 1Mbps	CAN	3.00	3.60	3.30	1000	\N	1.20	SOIC-8	3.3V native — direct connection to STM32 without level shifter. Classic CAN.	{can,3.3v,low-cost}	2026-05-14 00:01:58.273431+05:30
46e781e1-ecb9-4baf-8ac7-b7e6358c3a1c	MCP2551-I/SN	Microchip	can_transceiver	CAN Bus Transceiver 5V, 1Mbps	CAN	4.50	5.50	5.00	1000	\N	0.95	SOIC-8	5V — requires 3.3V level shifter for STM32. Very low cost, wide availability.	{can,5v,5v-logic,level-shift-needed}	2026-05-14 00:01:58.273431+05:30
4614ff7d-973c-455a-9065-cceaeb92c402	TCAN4550RGOT	Texas Instruments	can_transceiver	CAN-FD Controller+Transceiver via SPI, 8Mbps	SPI	3.00	5.50	3.30	8000	\N	4.20	VQFN-20	Adds CAN-FD capability to any MCU via SPI. Useful when MCU lacks native CAN.	{can-fd,spi,expander}	2026-05-14 00:01:58.273431+05:30
f769f1e3-19f3-495c-b416-6a7a482a4dd4	L6230PD	STMicroelectronics	motor_driver	BLDC Motor Driver, 3-phase, 2.8A	SPI	8.00	52.00	3.30	\N	\N	4.50	PowerSO-36	ST native, designed to work with STM32. 3-phase BLDC up to 2.8A/ch.	{bldc,3-phase,stm32,spi}	2026-05-14 00:01:58.273431+05:30
ba4b3106-ec36-4c11-bf72-1683f9451d77	DRV8305NPHP	Texas Instruments	motor_driver	3-Phase BLDC Gate Driver, SPI, 60V	SPI	6.00	60.00	3.30	\N	\N	4.80	HTSSOP-56	Gate driver only (external FETs needed). SPI configuration. High voltage.	{bldc,gate-driver,60v,spi}	2026-05-14 00:01:58.273431+05:30
0ced339f-5e43-4268-a012-2f3b4ab76c66	TMC2209-LA-T	Trinamic	motor_driver	Stepper Motor Driver, UART, 256 microsteps, 2A	UART	4.75	29.00	3.30	\N	\N	3.20	QFN-28	Silent step chopper stepper driver. UART/Step-Dir interface. 3.3V logic.	{stepper,uart,silent,2a}	2026-05-14 00:01:58.273431+05:30
2e756ccc-476e-4df8-8672-b41f5021a414	STSPIN32F0A	STMicroelectronics	motor_driver	3-Phase Gate Driver + STM32F0 MCU	SPI	8.00	45.00	3.30	\N	\N	3.90	QFN-48	Integrated gate driver + embedded STM32F0 MCU for standalone operation.	{bldc,integrated,stm32,gate-driver}	2026-05-14 00:01:58.273431+05:30
f7bf4f8a-04e5-4733-93e2-aed4922132eb	TPS65987D	Texas Instruments	pmic	USB-C PD Controller + Power Switch	I2C	3.00	20.00	3.30	\N	\N	3.50	VQFN-64	Manages USB-C Power Delivery negotiation. I2C config. Works with STM32.	{usb-c,pd,power,i2c}	2026-05-14 00:01:58.273431+05:30
7367ffba-7e95-4ae3-93e0-dc16fae86d11	STM32G431KBT6	STMicroelectronics	pmic	Companion MCU for motor control (not a PMIC but commonly paired)	SPI	1.71	3.60	3.30	\N	\N	3.20	LQFP-32	Co-processor role in dual-MCU designs.	{companion-mcu,motor}	2026-05-14 00:01:58.273431+05:30
9c3a99eb-8da5-47b1-8df3-4b05e2b8085f	AP7361C-33E	Diodes Inc	ldo	3.3V LDO Regulator, 1A, Low Dropout	Analog	3.50	6.00	3.30	\N	\N	0.30	SOT-89-5	3.3V output for STM32 power supply from 5V. 1A output. Very low cost.	{ldo,3.3v,1a,power-supply}	2026-05-14 00:01:58.273431+05:30
40b2d9aa-1953-441e-a5aa-468204c9bd7b	MP2359DJ-LF-Z	Monolithic Power	pmic	3A Buck Converter, 24V input, 0.81V-15V output	Analog	4.50	24.00	3.30	\N	\N	0.65	SOT-23-6	Step-down regulator. Input up to 24V. Suitable for 12V automotive → 3.3V rails.	{buck,24v,3a,automotive}	2026-05-14 00:01:58.273431+05:30
0e1aac7b-b026-4db8-a890-6ffafdbfdaa0	BMI270	Bosch	imu	6-axis IMU (Accel+Gyro), SPI/I2C, Ultra-low Power	SPI	1.71	3.60	3.30	\N	\N	1.20	LGA-14	SmartSense IMU for wearables/robotics. AI on-chip. < 0.95mA. SPI or I2C.	{imu,6-axis,spi,i2c,low-power}	2026-05-14 00:01:58.273431+05:30
b1f58efa-9995-47c2-a62b-6cf470d340fe	ICM-42688-P	InvenSense	imu	6-axis IMU, SPI/I2C, 3.2kHz ODR, ±2000°/s	SPI	1.71	3.60	3.30	\N	\N	2.50	LGA-14	High-performance IMU for drones/robotics. Very low noise. SPI/I2C.	{imu,6-axis,drone,high-perf}	2026-05-14 00:01:58.273431+05:30
ae9b6258-4caf-4d5e-ad84-0e8b6937688e	LSM6DSOX	STMicroelectronics	imu	6D IMU with Machine Learning Core, SPI/I2C	SPI	1.71	3.60	3.30	\N	\N	1.80	LGA-14	ST native IMU. ML core for gesture detection. Designed for STM32 ecosystem.	{imu,ml-core,st,spi,i2c}	2026-05-14 00:01:58.273431+05:30
99f0def7-c861-4b10-9844-b1a0624a1654	BMP390	Bosch	sensor	Barometric Pressure Sensor, I2C/SPI, ±0.5m altitude accuracy	I2C	1.65	3.60	3.30	\N	\N	1.10	LGA-10	Precision barometric sensor for altitude/weather. I2C or SPI. Low power.	{pressure,altitude,i2c,spi,weather}	2026-05-14 00:01:58.273431+05:30
cd266d56-5b2d-45bc-b095-1e564179f0f9	THVD1500DR	Texas Instruments	rs485	RS-485/RS-422 Transceiver, 3.3V, 50Mbps	UART	3.00	3.60	3.30	50000	\N	0.90	SOIC-8	3.3V RS-485 transceiver. 50Mbps. Auto-enable for half-duplex.	{rs485,uart,3.3v,50mbps}	2026-05-14 00:01:58.273431+05:30
b2925ae2-5b42-4b8e-b4a6-77fa85b6933c	SP3485EN-L/TR	MaxLinear	rs485	RS-485 Transceiver, 3.3V, 10Mbps, 1/8 Unit Load	UART	3.00	3.60	3.30	10000	\N	0.55	SOIC-8	Low-cost 3.3V RS-485. 1/8 unit load (up to 256 nodes on bus).	{rs485,uart,3.3v,low-cost}	2026-05-14 00:01:58.273431+05:30
\.


--
-- PostgreSQL database dump complete
--

\unrestrict jciB9LTLrmTic7U3Hz8Ei2hAYUAKNj1VC09slzz5SkIVd5Jkhemjoo9x4FG05R0

