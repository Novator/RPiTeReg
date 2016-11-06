#!/bin/sh

# The script for running RPi Home Thermo Regulator
# 2012 (c) Michael Galyuk, free software, GNU GPLv2


DIRFILE=`readlink -e "$0"`
CURFILE=`basename "$DIRFILE"`
CURDIR=`dirname "$DIRFILE"`

cd "$CURDIR"

screen -x "rpitereg"
if [ "$?" != "0" ]; then
  #screen -fn -h 1000 -S rpitereg {`which python` ./rpitereg.py | tee -a ./rpitereg.log}
  screen -fn -h 1000 -S "rpitereg" `which python` ./rpitereg.py
fi

