#!/bin/sh

RC=`ps -few | grep "rpitereg" | wc -l`

if [ "$RC" -gt "3" ]; then
  echo "Уже запущена копия: "$RC
  exit 1
fi

cd /root/rpitereg/
#/bin/su root -c "/usr/bin/screen -dm -S rpitereg bash -c '/usr/bin/python /root/rpitereg/rpitereg.py'"
#/usr/bin/screen -dm -S rpitereg bash -c '/usr/bin/python /root/rpitereg/rpitereg.py'
/usr/bin/screen -fn -h 1000 -dm -S "rpitereg" /usr/bin/python ./rpitereg.py

