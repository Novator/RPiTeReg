#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# RPi Home Thermo Regulator
# 2016 (c) Michael Galyuk, GNU GPLv2

import time, datetime, sys, fcntl, termios, os, glob, ConfigParser
import RPi.GPIO as GPIO

# GPIO constants
PinGpio17 = 11
PinGpio27 = 13

# Time periods (sec)
AimTemp = 23.0
WorkSec = 45
RestSec = 50
CorrSec = 4
MinRestSec = 10
MaxRestSec = 150
TempRelax = 0.5
SensorDev = '/sys/bus/w1/devices/28*'
WarmZone = 1.5
ColdZone = 1.5

# Load OS modules for wire1
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')


# Get parameter value from config
# RU: Взять значение параметра из конфига
def getparam(sect, name, akind='str'):
  global config
  res = None
  try:
    if akind=='int':
      res = config.getint(sect, name)
    elif akind=='bool':
      res = config.getboolean(sect, name)
    elif akind=='real':
      res = config.getfloat(sect, name)
    else:
      res = config.get(sect, name)
  except:
    res = None
  return res

# Open config file and read parameters
# RU: Открыть конфиг и прочитать параметры
config = ConfigParser.SafeConfigParser()
res = config.read('./rpitereg.ini')
if len(res):
  aim_temp = getparam('common', 'aim_temp', 'real')
  work_sec = getparam('common', 'work_sec', 'int')
  rest_sec = getparam('common', 'rest_sec', 'int')
  corr_sec = getparam('common', 'corr_sec', 'int')
  temp_relax = getparam('common', 'temp_relax', 'real')
  min_rest = getparam('common', 'min_rest', 'int')
  max_rest = getparam('common', 'max_rest', 'int')
  warm_zone = getparam('common', 'warm_zone', 'real')
  cold_zone = getparam('common', 'cold_zone', 'real')
  sensor_dev = getparam('common', 'sensor_dev')

# Set default config values
# RU: Задать параметры по умолчанию
if not aim_temp: aim_temp = AimTemp
if not work_sec: work_sec = WorkSec
if not rest_sec: rest_sec = RestSec
if not corr_sec: rest_sec = CorrSec
if not temp_relax: temp_relax = TempRelax
if not min_rest: min_rest = MinRestSec
if not max_rest: min_rest = MaxRestSec
if not warm_zone: warm_zone = WarmZone
if not cold_zone: cold_zone = ColdZone
if not sensor_dev: sensor_dev = SensorDev

# Detect first thermo sensor
device_file = None
device_files = glob.glob(sensor_dev)
if len(device_files)>0:
  device_file = device_files[0] + '/w1_slave'

# Read raw data from thermo sensor
def read_temp_raw():
  lines = None
  if device_file:
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
  return lines

# Read and parse correct temperature
def read_temp():
  temp = None
  lines = read_temp_raw()
  attempt = 0
  while lines and (lines[0].strip()[-3:] != 'YES') and (attempt < 20):
    attempt += 1
    time.sleep(0.2)
    lines = read_temp_raw()
  if lines:
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
      temp_string = lines[1][equals_pos+2:]
      temp = float(temp_string) / 1000.0
  return temp

# Set GPIO pins
def set_gpio(mode=0):
  GPIO.output(PinGpio17, mode)
  GPIO.output(PinGpio27, mode)


# Preparation for key capturing in terminal
fd = sys.stdin.fileno()
oldterm = termios.tcgetattr(fd)
newattr = termios.tcgetattr(fd)
newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
termios.tcsetattr(fd, termios.TCSANOW, newattr)
oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

try:
  print('RPi Home Thermo Regulator 0.3')
  print('Work='+str(work_sec)+'s Rest='+str(rest_sec)+'s Corr='+str(corr_sec)+ \
    's Relax='+str(temp_relax)+'s Min/Max=' +str(min_rest)+'/'+str(max_rest)+'s')
  print('Sensor: '+str(device_file)+' ('+sensor_dev+')')
  cur_time = datetime.datetime.now()
  time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
  temp = read_temp()
  print('AimTemp='+str(aim_temp)+'C Temp='+str(temp)+'C Warm/ColdZone='+ \
    str(warm_zone)+'/'+str(cold_zone)+' '+time_str)

  GPIO.setmode(GPIO.BOARD)
  GPIO.setup(PinGpio17, GPIO.OUT)
  GPIO.setup(PinGpio27, GPIO.OUT)

  print('GPIO control is active...')
  print('Press Q to stop and quit.')
  print('(screen: Ctrl+A,D - detach, Ctrl+A,K - kill, "screen -r" to resume)')
  prev_temp = temp
  prev2_temp = None
  last_actual_rest_sec = None
  curr_rest_sec = rest_sec
  need_calc = True
  heat_mode = 5
  time_sec = work_sec
  working = True
  while working:
    #print('time_sec='+str(time_sec)+' heat_mode='+str(heat_mode))
    if heat_mode<=0:
      if time_sec>=curr_rest_sec:
        if heat_mode != -1:
          set_gpio(1)
        heat_mode = 1
        time_sec = 0
    elif time_sec>=(work_sec-10):
      time_diff = 0
      if need_calc:
        start_time = datetime.datetime.now()
        temp = read_temp()
        #print('==111Temp='+str(temp)+'C RestSec='+str(curr_rest_sec))
        curr_rest_sec0 = curr_rest_sec
        rest_diff = None
        if temp and (temp>0) and (temp<65):
          need_calc = False
          if temp<aim_temp-cold_zone:
            if (heat_mode==1) or (heat_mode==5):
              heat_mode += 1
            #time_sec = 0
            #need_calc = True
            if curr_rest_sec>min_rest:
              last_actual_rest_sec = curr_rest_sec
            curr_rest_sec = min_rest
            cur_time = datetime.datetime.now()
            time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
            print(time_str+'  ColdZone! Temp='+str(temp)+'C Prev='+str(prev_temp)+ \
              ' MinRest='+str(curr_rest_sec)+'s')
          elif temp>aim_temp+warm_zone:
            heat_mode = -1
            time_sec = work_sec
            cur_time = datetime.datetime.now()
            time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
            print(time_str+'  WarmZone! Temp='+str(temp)+'C Prev='+str(prev_temp)+ \
              ' No Work (Rest='+str(curr_rest_sec)+'s)')
          else:
            if not (last_actual_rest_sec is None):
              curr_rest_sec = last_actual_rest_sec
              last_actual_rest_sec = None
            if heat_mode != 5:
              heat_mode = 1
            temp_diff = temp - aim_temp
            rest_diff = corr_sec * temp_diff
            if prev_temp:
              temp_step = temp - prev_temp
              if (abs(temp_diff) < temp_relax) \
              and (((rest_diff>0) and (temp_step<0)) \
              or ((rest_diff<0) and (temp_step>0))):
                rest_diff = 0
            #print('==Temp='+str(temp)+'C  Prev='+str(prev_temp)+'C  RestDiff='+str(rest_diff)+'s')
            if ((curr_rest_sec+rest_diff)>=0) and ((curr_rest_sec+rest_diff)>=min_rest) \
            and (curr_rest_sec+rest_diff<=max_rest):
              curr_rest_sec += rest_diff
          prev2_temp = prev_temp
          prev_temp = temp
        else:
          curr_rest_sec = rest_sec
        if (curr_rest_sec0 != curr_rest_sec):
          cur_time = datetime.datetime.now()
          time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
          print(time_str+'  Temp='+str(temp)+'C Prev='+str(prev2_temp)+ \
            'C RestDiff='+str(rest_diff)+'s Rest='+str(curr_rest_sec)+'s')
        end_time = datetime.datetime.now()
        time_diff = int(round((end_time - start_time).total_seconds()))
      if heat_mode>=5:
        heat_mode -= 4
        set_gpio(1)
        time_sec = 0
      if time_sec>=work_sec:
        need_calc = True
        time_sec = time_diff
        if time_sec<curr_rest_sec:
          if heat_mode>0:
            heat_mode = 0
          set_gpio(0)
      else:
        time_sec += time_diff
    try:
      #tty.setraw(sys.stdin.fileno())
      c = sys.stdin.read(1)
      if (c=='q') or (c=='Q') or (c=='x') or (c=='X') or (ord(c)==185) or (ord(c)==153):
        working = False
    #except IOError: pass
    except: pass
    if working:
      time.sleep(1)
    time_sec += 1

finally:
  set_gpio(0)
  termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
  fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
  GPIO.cleanup()
  sys.exit()

