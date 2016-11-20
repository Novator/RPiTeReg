
=== RPi Home Thermo Regulator

Contents

1) overview
2) system requirements
3) installation in Raspbian
4) usage
5) getting help


1. OVERVIEW

RPiTeReg is a small python utility for controling the electro heater
at home by thermo sensor. It works at smart home automatics and maintains
temperature with control a relay.

The utility does permanent iterations with work and rest period of heater.
Work and rest periods endlessly alternating one after another. Work period
is constant. Rest period is variable through a calculating correction to achive
assigned aim temperature.

See the scheme of connection:

-------
|     |-------> thermo sensor
| RPi |3.3V           220V
|     |-------[relay]=====[heater]
-------


2. SYSTEM REQUIREMENTS

- Raspberry Pi computer with Raspbian OS
- Thermo sensor Dallas DS18B20 or similar
- Solid-state or mechanical relay
- Electrical heater
- Python2.7 script engine
- Screen utility


3. INSTALLATION IN RASPBIAN

1) Make directory with root user, for example:

  mkdir /root/rpitereg

2) Copy all files (https://github.com/Novator/RPiTeReg/archive/master.zip) to there
3) Install screen

  apt-get install screen

4) Connect relay bindings to GPIO17 (pin 11) or GPIO27 (13)
if you use 26-pin RPi B (ver 2) (change a python code if you
use another release of RPi)

5) Connect thermal sensor to GPIO4 (pin 7) with pull-up resistor 4.7kOm

6) To run and check the programm use one of these commands in terminal:

  /root/rpitereg/rpitereg.sh
  python /root/rpitereg/rpitereg.py
  python2.7 /root/rpitereg/rpitereg.py

7) Add a line to end of file /etc/rc.local, but above "exit 0":

  /root/rpitereg/rpitereg.rc.sh &

The programm will autorun on each boot of RPi.


4. USAGE

Check parameters at /root/rpitereg/rpitereg.ini:

aim_temp - aim temperature in Celsius (С)
work_sec - constant work heater period (in seconds)
rest_sec - initial rest period (utility will be changing it for each iteration)
corr_sec - rest correction step for 1(С) degree deviation from aim temperature
sensor_dev - mask for finding thermo sensor, will be taken a first
temp_relax - no rest correction zone near aim temperature (C)
min_rest - minimal allowable rest period (C)
max_rest - maximal allowable rest period (C)
cold_zone - cold zone (C) underlying aim temp when rest period forced to minimal
warm_zone - warm zone (C) overlying aim temp where heater will be switched off
flush_interval - interval in seconds forced a writing portion of log to file

To run and resume utility use /root/rpitereg/rpitereg.sh.
The utility automatically reload configuration file when you edit it
and will use new parameterswithout necessity to restart the script.
You can use ssh or http to rule parameters via controlling ini-file.


5. GETTING HELP

Ask author for help:

  http://facebook.com/robux
  http://vk.com/robux
  robux@mail.ru
  Michael Galyuk

Support development:

  BitCoin: 1PanDR1Q6TL3qE1TSs2Zagt2ihhEiCBHZB

