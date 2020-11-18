#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# RPi Home Thermo Regulator
# 2016 (c) Michael Galyuk, GNU GPLv2

import time, datetime, sys, fcntl, termios, os, glob, ConfigParser, requests
import RPi.GPIO as GPIO

# GPIO constants
PinGpio4  = 7
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
SetparInt = 300
TunnelWorkTime = 3600

ConfigIni1 = '/var/www/html/rpitereg.ini'
ConfigIni2 = './rpitereg.ini'

# Load OS modules for wire1
#os.system('modprobe w1-gpio')
#os.system('modprobe w1-therm')

#Global setup parameters
#[common]
flush_time = None
curlogindex = None
curlogsize = None
max_size = 102400
flush_interval = 480
#[log]
log_prefix = 'rpitereg'
log_path = '.'
#[internet]
setpar_url = None
setpar_interval = SetparInt

#Global variables
logfile = None

# ====================================================================
# Log functions
# RU: Функции логирования

# Get filename of log by index
# RU: Взять имя файла лога по индексу
def logname_by_index(index=1):
  global log_prefix, log_path
  filename = None
  if log_prefix and (len(log_prefix)>0):
    filename = log_prefix
    if (not log_path) or (len(log_path)<=1):
      log_path = os.path.abspath('.')
    filename = log_path + '/' + filename
    filename = os.path.abspath(filename+str(index)+'.log')
  return filename

# Close active log file
# RU: Закрыть активный лог файл
def closelog():
  global logfile
  if logfile:
    logfile.close()
    logfile = None

# Write string to log file (and to screen)
# RU: Записать строку в лог файл (и на экран)
def logmes(mes, show=True):
  global logfile, flush_time, curlogindex, curlogsize, log_prefix, max_size, flush_interval
  if (not logfile) and (logfile != False):
    if log_prefix and (len(log_prefix)>0):
      try:
        s1 = os.path.getsize(logname_by_index(1))
      except:
        s1 = None
      try:
        s2 = os.path.getsize(logname_by_index(2))
      except:
        s2 = None
      curlogindex = 1
      curlogsize = s1
      if (s1 and ((s1>=max_size) or (s2 and (s2<s1)))):
        curlogindex = 2
        curlogsize = s2
      try:
        filename = logname_by_index(curlogindex)
        logfile = open(filename, 'a')
        if not curlogsize: curlogsize = 0
        print('Logging to file: '+filename)
      except:
        logfile = False
        print('Cannot open log-file: '+str(filename))
    else:
      logfile = False
      print('Logging to file is off.')
  if logfile or show:
    cur_time = datetime.datetime.now()
    time_str = cur_time.strftime('%Y.%m.%d %H:%M:%S')
    mes = str(mes)
    if show: print('Log'+time_str[-14:]+': '+mes)
    if logfile:
      logline = time_str+': '+mes+'\n'
      curlogsize += len(logline)
      if curlogsize >= max_size:
        curlogsize = 0
        if curlogindex == 1:
          curlogindex = 2
        else:
          curlogindex = 1
        try:
          filename = logname_by_index(curlogindex)
          closelog()
          logfile = open(filename, 'w')
          print('Change logging to file: '+filename)
        except:
          logfile = False
          print('Cannot change log-file: '+filename)
          return
      logfile.write(logline)
      if (not flush_time) or (cur_time >= (flush_time + datetime.timedelta(0, flush_interval))):
        logfile.flush()
        flush_time = cur_time


# ====================================================================
# Setup functions
# RU: Настроечные функции

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
work_cfg_ini = None
aim_temp = 23.0
sheduler_mode = 1
shedulers = []

def add_shed_line(line, to_clear=None):
  global shedulers
  res = False
  if to_clear:
    del shedulers[:]
  if line:
    line = line.split(';')
    if line and (len(line)>=3):
      time_str = line[1]
      time_str = time_str.split(':')
      hour = int(time_str[0])
      minute = int(time_str[1])
      line[1] = hour*60 + minute
      temp = float(line[2])
      line[2] = temp
      #print('Add shed string')
      #print(line)
      shedulers.append(line)
    res = True
  return res

# Clear all config options in the memory
def clear_config_options(config):
  for section in config.sections():
    for option in config.options(section):
      config.remove_option(section, option)

# Try to read config parameters
def read_config(cfg_ini=None, mtime=None, def_set=False):
  global last_config_mtime, device_file, work_cfg_ini, \
    aim_temp, sheduler_mode, work_sec, rest_sec, corr_sec, temp_relax, \
    min_rest, max_rest, warm_zone, cold_zone, sensor_dev, setpar_url, \
    setpar_interval, log_prefix, log_path, flush_interval

  res = False
  if (cfg_ini==None):
    cfg_ini = work_cfg_ini
  if (mtime==None):
    mtime = get_file_mod_time(cfg_ini)
  last_config_mtime = mtime
  if mtime>0:
    clear_config_options(config)
    res = config.read(cfg_ini)
    if len(res):
      res = True
      work_cfg_ini = cfg_ini
      aim_temp = getparam('common', 'aim_temp', 'real')
      sheduler_mode = getparam('common', 'sheduler_mode', 'int')
      sheduler1 = getparam('common', 'sheduler1')
      sheduler2 = getparam('common', 'sheduler2')
      sheduler3 = getparam('common', 'sheduler3')
      sheduler4 = getparam('common', 'sheduler4')
      sheduler5 = getparam('common', 'sheduler5')
      sheduler6 = getparam('common', 'sheduler6')
      sheduler7 = getparam('common', 'sheduler7')
      sheduler8 = getparam('common', 'sheduler8')
      sheduler9 = getparam('common', 'sheduler9')
      work_sec = getparam('common', 'work_sec', 'int')
      rest_sec = getparam('common', 'rest_sec', 'int')
      corr_sec = getparam('common', 'corr_sec', 'real')
      temp_relax = getparam('common', 'temp_relax', 'real')
      min_rest = getparam('common', 'min_rest', 'int')
      max_rest = getparam('common', 'max_rest', 'int')
      warm_zone = getparam('common', 'warm_zone', 'real')
      cold_zone = getparam('common', 'cold_zone', 'real')
      sensor_dev = getparam('common', 'sensor_dev')
      log_prefix = getparam('log', 'log_prefix')
      log_path = getparam('log', 'log_path')
      flush_interval = getparam('log', 'flush_interval', 'int')
      setpar_url = getparam('internet', 'setpar_url')
      setpar_interval = getparam('internet', 'setpar_interval', 'int')

      add_shed_line(sheduler1, True)
      add_shed_line(sheduler2)
      add_shed_line(sheduler3)
      add_shed_line(sheduler4)
      add_shed_line(sheduler5)
      add_shed_line(sheduler6)
      add_shed_line(sheduler7)
      add_shed_line(sheduler8)
      add_shed_line(sheduler9)

  if res or def_set:
    # Set defaults if need
    if not aim_temp: aim_temp = AimTemp
    #if not sheduler_mode: sheduler_mode = 1
    if not work_sec: work_sec = WorkSec
    if not rest_sec: rest_sec = RestSec
    if not corr_sec: corr_sec = CorrSec
    if not temp_relax: temp_relax = TempRelax
    if not min_rest: min_rest = MinRestSec
    if not max_rest: max_rest = MaxRestSec
    if not warm_zone: warm_zone = WarmZone
    if not cold_zone: cold_zone = ColdZone
    if not sensor_dev: sensor_dev = SensorDev
    if not setpar_interval: setpar_interval = SetparInt
    # Show config parameters
    #mtime = time.ctime(mtime)
    #mtime = time.localtime(mtime)
    mtime = datetime.datetime.fromtimestamp(mtime)
    time_str = mtime.strftime('%Y.%m.%d %H:%M:%S')
    logmes('---Config ['+cfg_ini+'] modified: '+time_str)
    logmes('Work='+str(work_sec)+'s Rest='+str(rest_sec)+'s Corr='+str(corr_sec)+ \
      's Relax='+str(temp_relax)+'s Min/Max=' +str(min_rest)+'/'+str(max_rest)+'s')
    # Detect first thermo sensor
    device_files = glob.glob(sensor_dev)
    if len(device_files)>0:
      device_file = device_files[0] + '/w1_slave'
    logmes('Sensor: '+str(device_file)+' ('+sensor_dev+')')
    logmes('SetPar: URL="'+str(setpar_url)+'" Int='+str(setpar_interval)+'s')
    if sheduler_mode>0:
      logmes('Shedulers: '+str(shedulers))
    logmes('AimTemp='+str(aim_temp)+'C Warm/ColdZone='+ \
      str(warm_zone)+'/'+str(cold_zone)+' Sheduler_mode='+str(sheduler_mode))
  return res

def read_sheduler_temp(cur_time=None):
  global shedulers
  res = None
  if len(shedulers)>0:
    if not cur_time:
      cur_time = datetime.datetime.now()
    day = str(cur_time.weekday()+1)  #1..7
    time = cur_time.hour*60 + cur_time.minute
    aim_temp_shed = None
    for line in shedulers:
      s_days = line[0]
      s_time = line[1]
      s_temp = line[2]
      if (day in s_days) and (time>=s_time):
        res = s_temp
        #logmes('read_shed res= '+str(res)+' ('+str(line)+')')
      elif res:
        break
  return res

# ====================================================================
# Remote setup
# RU: Удалённая настройка

last_setpar_get_time = None
start_ssh_tunnel_time = None

# Try to read setpar.txt from remote and update temp and up ssh-tunnel
def process_setpar():
  global aim_temp, setpar_url, setpar_interval, last_setpar_get_time, start_ssh_tunnel_time
  if setpar_url and (len(setpar_url)>0):
    cur_time = datetime.datetime.now()
    if ((last_setpar_get_time is None) \
    or (cur_time >= (last_setpar_get_time + datetime.timedelta(0, setpar_interval)))):
      url = setpar_url
      try:
        req = requests.get(url+'txt')
      except:
        req = None
      if req:
        last_setpar_get_time = cur_time
        body = req.content
        body_len = len(body)
        if (body_len>=4) and (body_len<=8):
          sign = body[0:4]
          temp = body[4:body_len]
          logmes('---SetPar ['+str(sign)+'|'+str(temp)+']')
          try:
            req = requests.get(url+'php?clear=1')
          except:
            req = None
          if (sign=='VVVV') or (sign=='TTTT'):
            if temp:
              val = 0
              try:
                val = float(temp)
              except:
                val = 0
              if (val>0) and (val<=25):
                aim_temp = val
                logmes('AimTemp='+str(aim_temp)+'C')
            if (sign=='VVVV'):
              os.system('/root/rpitereg/tunnel/kill-tunnel.rc.sh')
              os.system('/root/rpitereg/tunnel/open-tunnel.rc.sh &')
              start_ssh_tunnel_time = cur_time
    if (start_ssh_tunnel_time \
    and (cur_time >= (start_ssh_tunnel_time + datetime.timedelta(0, TunnelWorkTime)))):
      os.system('/root/rpitereg/tunnel/kill-tunnel.rc.sh')
      start_ssh_tunnel_time = None
      logmes('Tunnel is closed')


# ====================================================================
# GPIO working functions
# RU: Функции работы с GPIO

# Read raw data from thermo sensor
# RU: Читать сырые данные с термо датчика
def read_temp_raw():
  lines = None
  if device_file:
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
  return lines

# Read and parse correct temperature
# RU: Читать и распознать корректную температуру
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

# Set state of GPIO pins
# Задать состояние GPIO контактов
def set_gpio(mode=0):
  GPIO.output(PinGpio27, mode)
  GPIO.output(PinGpio17, mode)


# === Running the utility
# === RU: Запуск утилиты

print('RPi Home Thermo Regulator 0.5')
if not read_config(ConfigIni1):
  read_config(ConfigIni2, None, True)

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
  logmes('===Start Temp='+str(temp)+'C')

  GPIO.setmode(GPIO.BOARD)
  GPIO.setup(PinGpio27, GPIO.OUT)
  GPIO.setup(PinGpio17, GPIO.OUT)

  #os.system('modprobe -r w1-therm')
  #os.system('modprobe -r w1-gpio')
  #time.sleep(0.3)
  #GPIO.setup(PinGpio4, GPIO.OUT)
  #GPIO.output(PinGpio4, 0)
  #time.sleep(1)
  #GPIO.output(PinGpio4, 1)
  #GPIO.cleanup()
  #os.system('modprobe w1-gpio')
  #os.system('modprobe w1-therm')
  #time.sleep(1)
  #GPIO.setmode(GPIO.BOARD)
  #GPIO.setup(PinGpio17, GPIO.OUT)
  #GPIO.setup(PinGpio27, GPIO.OUT)

  print('GPIO control is captured.')
  print('Press Q to stop and quit.')
  if (os.environ['TERM']=='screen'):
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
        need_calc = True
    elif time_sec>=(work_sec-15):
      time_diff = 0
      if need_calc:
        start_time = datetime.datetime.now()
        if sheduler_mode>0:
          aim_temp_new = read_sheduler_temp(start_time)
          if aim_temp_new and ((aim_temp != aim_temp_new) or (sheduler_mode>1)):
            aim_temp = aim_temp_new
            logmes('Sheduler AimTemp='+str(aim_temp)+'C')
        temp = read_temp()
        process_setpar()
        #print('==111Temp='+str(temp)+'C RestSec='+str(curr_rest_sec))
        curr_rest_sec0 = curr_rest_sec
        rest_diff = None
        if temp and (temp>0) and (temp<65):
          need_calc = False
          if work_cfg_ini:
            config_mtime = get_file_mod_time(work_cfg_ini)
            if (last_config_mtime != config_mtime):
              read_config(work_cfg_ini, config_mtime)
              need_calc = True
          if temp<aim_temp-cold_zone:
            if (heat_mode==1) or (heat_mode==5):
              heat_mode += 1
            #time_sec = 0
            #need_calc = True
            if (curr_rest_sec>min_rest) or (last_actual_rest_sec==None):
              last_actual_rest_sec = curr_rest_sec
              curr_rest_sec0 = min_rest
            curr_rest_sec = min_rest
            logmes('ColdZone! Temp='+str(temp)+'C Prev='+str(prev_temp)+ \
              ' [Min]Rest='+str(curr_rest_sec)+'s (LastRest='+str(last_actual_rest_sec)+')')
          elif temp>aim_temp+warm_zone:
            heat_mode = -1
            time_sec = work_sec
            logmes('WarmZone! Temp='+str(temp)+'C Prev='+str(prev_temp)+ \
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
              if (abs(temp_diff) <= temp_relax) \
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
          logmes('Temp='+str(temp)+'C Prev='+str(prev2_temp)+ \
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
  closelog()

