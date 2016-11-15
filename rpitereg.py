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
RestSec = 60
CorrSec = 4
MinRestSec = 10
MaxRestSec = 150
TempRelax = 0.5
SensorDev = '/sys/bus/w1/devices/28*'
WarmZone = 1.5
ColdZone = 1.5

ConfigIni = './rpitereg.ini'

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

# Get last modification time of file
def get_file_mod_time(filename):
  try:
    mtime = os.path.getmtime(filename)
  except OSError:
    mtime = 0
  #mtime = datetime.fromtimestamp(mtime)
  #mtime = time.localtime(mtime)
  return mtime

# Open config file and read parameters
# RU: Открыть конфиг и прочитать параметры
config = ConfigParser.SafeConfigParser()
last_config_mtime = 0
device_file = None

# Try to read config parameters
def read_config(cfg_ini, mtime=None):
  global last_config_mtime, device_file
  global aim_temp, work_sec, rest_sec, corr_sec, temp_relax, min_rest, max_rest, \
    warm_zone, cold_zone, sensor_dev
  if (mtime==None):
    mtime = get_file_mod_time(cfg_ini)
  last_config_mtime = mtime
  if mtime>0:
    res = config.read(cfg_ini)
    if len(res):
      aim_temp = getparam('common', 'aim_temp', 'real')
      work_sec = getparam('common', 'work_sec', 'int')
      rest_sec = getparam('common', 'rest_sec', 'int')
      corr_sec = getparam('common', 'corr_sec', 'real')
      temp_relax = getparam('common', 'temp_relax', 'real')
      min_rest = getparam('common', 'min_rest', 'int')
      max_rest = getparam('common', 'max_rest', 'int')
      warm_zone = getparam('common', 'warm_zone', 'real')
      cold_zone = getparam('common', 'cold_zone', 'real')
      sensor_dev = getparam('common', 'sensor_dev')
  # Set defaults if need
  if not aim_temp: aim_temp = AimTemp
  if not work_sec: work_sec = WorkSec
  if not rest_sec: rest_sec = RestSec
  if not corr_sec: corr_sec = CorrSec
  if not temp_relax: temp_relax = TempRelax
  if not min_rest: min_rest = MinRestSec
  if not max_rest: max_rest = MaxRestSec
  if not warm_zone: warm_zone = WarmZone
  if not cold_zone: cold_zone = ColdZone
  if not sensor_dev: sensor_dev = SensorDev
  # Show config parameters
  #mtime = time.ctime(mtime)
  #mtime = time.localtime(mtime)
  mtime = datetime.datetime.fromtimestamp(mtime)
  time_str = mtime.strftime('%Y.%m.%d %H:%M:%S')
  print('Config ['+cfg_ini+'] modified: '+time_str)

  cur_time = datetime.datetime.now()
  time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
  print('Work='+str(work_sec)+'s Rest='+str(rest_sec)+'s Corr='+str(corr_sec)+ \
    's Relax='+str(temp_relax)+'s Min/Max=' +str(min_rest)+'/'+str(max_rest)+'s')
  # Detect first thermo sensor
  device_files = glob.glob(sensor_dev)
  if len(device_files)>0:
    device_file = device_files[0] + '/w1_slave'
  print('Sensor: '+str(device_file)+' ('+sensor_dev+')')
  print('AimTemp='+str(aim_temp)+'C Warm/ColdZone='+ \
    str(warm_zone)+'/'+str(cold_zone)+' '+time_str)


print('RPi Home Thermo Regulator 0.4')
read_config(ConfigIni)


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
  temp = read_temp()
  print('Temp='+str(temp)+'C')

  GPIO.setmode(GPIO.BOARD)
  GPIO.setup(PinGpio17, GPIO.OUT)
  GPIO.setup(PinGpio27, GPIO.OUT)

  print('GPIO control is active...')
  print('Press Q to stop and quit.')
  print('(screen: Ctrl+A,D - detach, Ctrl+A,K - kill, "screen -r" to resume)')
  trace_show = False
  prev_temp = temp
  prev2_temp = None
  last_actual_rest_sec = None
  curr_rest_sec = rest_sec
  need_calc = True
  heat_mode = 5
  time_sec = work_sec
  working = True
  while working:
    if trace_show:
      print('time_sec='+str(time_sec)+' heat_mode='+str(heat_mode))
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
          config_mtime = get_file_mod_time(ConfigIni)
          if (last_config_mtime != config_mtime):
            print('Reread config...')
            read_config(ConfigIni, config_mtime)
          if temp<aim_temp-cold_zone:
            if (heat_mode==1) or (heat_mode==5):
              heat_mode += 1
            #time_sec = 0
            #need_calc = True
            if (curr_rest_sec>min_rest) or (last_actual_rest_sec==None):
              last_actual_rest_sec = curr_rest_sec
              curr_rest_sec0 = min_rest
            curr_rest_sec = min_rest
            cur_time = datetime.datetime.now()
            time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
            print(time_str+'  ColdZone! Temp='+str(temp)+'C Prev='+str(prev_temp)+ \
              ' [Min]Rest='+str(curr_rest_sec)+'s (LastRest='+str(last_actual_rest_sec)+')')
          elif temp>aim_temp+warm_zone:
            print('555')
            heat_mode = -1
            time_sec = work_sec
            cur_time = datetime.datetime.now()
            time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
            print(time_str+'  WarmZone! Temp='+str(temp)+'C Prev='+str(prev_temp)+ \
              ' No Work (Rest='+str(curr_rest_sec)+'s)')
          else:
            if (last_actual_rest_sec != None):
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
            if trace_show:
              print('==Temp='+str(temp)+'C  Prev='+str(prev_temp)+'C RestDiff='+str(rest_diff)+'s Rest='+str(curr_rest_sec)+'s ')
            if ((curr_rest_sec+rest_diff)<min_rest):
              curr_rest_sec = min_rest
            elif ((curr_rest_sec+rest_diff)>max_rest):
              curr_rest_sec = max_rest
            elif ((curr_rest_sec+rest_diff)>=0):
              curr_rest_sec += rest_diff
          prev2_temp = prev_temp
          prev_temp = temp
        else:
          curr_rest_sec = rest_sec
        if (curr_rest_sec0 != curr_rest_sec) or trace_show:
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
      #print('key code: '+str(ord(c)))
      if (c=='q') or (c=='Q') or (c=='x') or (c=='X') or (ord(c)==185) or (ord(c)==153):
        working = False
      elif (c=='t') or (c=='T') or (ord(c)==181) or (ord(c)==149) or (ord(c)==32):
        trace_show = (not trace_show)
        print('Trace mode='+str(trace_show))
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

