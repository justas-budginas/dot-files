#!/bin/bash

#Compositor
killall picom
while pgrep -u $UID -x picom > /dev/null; do sleep 1; done
picom &

#Background
feh --randomize --bg-fill ~/wallpapers/* &
killall i3-layouts
i3-layouts &
