
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
Work period is constant. Rest period is variable to achive aim temperature.


2. SYSTEM REQUIREMENTS

- Raspberry Pi computer with Raspbian OS
- Thermo sensor Dallas DS18B20 or similar
- Solid-state or mechanical relay
- Electrical heater
- Python2.7 script engine
- Screen utility


3. INSTALLATION IN RASPBIAN

1) Make directrory with root user, for example:

  mkdir /root/rpitereg

2) Copy all files there
3) Add a line to file /etc/rc.local:

  /root/rpitereg/rpitereg.rc.sh &

4) Install screen

  apt-get install screen


4. USAGE

Check parameters at /root/rpitereg/rpitereg.ini:

aim_temp - aim temperature in Celsius (С)
work_sec - constant work heater period (in seconds)
rest_sec - start rest period when heater is off (utility will change it in interval)
corr_sec - rest correction for 1С degree delta
sensor_dev - mask for finding thermo sensor, will be taken first
temp_relax - offset when no rest correction (C)
min_rest - minimal rest interval (C)
max_rest - maximal rest interval (C)
cold_zone - cold zone (C) below aim temp where rest period sets to minimal
warm_zone - warm zone (C) upper aim temp where no heater work

To run and resume utility use /root/rpitereg/rpitereg.sh.


5. GETTING HELP

Ask author for help:

  http://facebook.com/robux
  http://vk.com/robux
  robux@mail.ru
  Michael Galyuk

Support development:

  BitCoin: 1PanDR1Q6TL3qE1TSs2Zagt2ihhEiCBHZB

