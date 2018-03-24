#!/bin/bash
# Copyright (C) 2018, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright 
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its 
#    contributors may be used to endorse or promote products derived 
#    from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, 
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# description: Jetson script to install Jetson clock service
# Reference:
# https://devtalk.nvidia.com/default/topic/1000657/script-for-maximum-clockspeeds-and-performence/
# 60sec delay only for release befor 28.1
# https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/

# Load environment variables:
# - JETSON_BOARD
# - JETSON_L4T (JETSON_L4T_RELEASE, JETSON_L4T_REVISION)
# - JETSON_DESCRIPTION
# - JETSON_CUDA
source /etc/jetson_easy/jetson_variables

JETSON_PERFORMANCE_WAIT_TIME=60
JETSON_EASY_FOLDER="/etc/jetson_easy"

status()
{
    echo "Status"
    echo "$JETSON_BOARD"
    echo "$(awk '{print int($1/3600)":"int(($1%3600)/60)":"int($1%60)}' /proc/uptime)"
    
    local TEST=$(sudo $HOME/jetson_clocks.sh --show)
    
    echo $TEST | sed -e 1b -e '$!d'
}

start()
{
    # Check which version is L4T is loaded
    # if is before the 28.1 require to launch jetson_clock.sh only 60sec before the boot
    # https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
    if [ $(echo $JETSON_L4T'>28.1' | bc -l) -eq 1 ]
    then
        # Time from boot 
        local BOOT_TIME=$(cat /proc/uptime | cut -f1 -d " ")
        # Wait a minute from boot before start
        if [ $(echo $BOOT_TIME'<'$((JETSON_PERFORMANCE_WAIT_TIME+1)) | bc -l) -eq 1 ] 
        then
            local TIME_TO_WAIT=$(echo $((JETSON_PERFORMANCE_WAIT_TIME+1))'-'$BOOT_TIME | bc)
            echo "Time to wait=$TIME_TO_WAIT"
            # Sleep for other time
            sleep $TIME_TO_WAIT
        fi
    fi
    
    if [ ! -f /tmp/jetson_performance_run ]
    then
        # check if exist l4t_dfs.conf otherwhise delete
        if [ -f $JETSON_EASY_FOLDER/l4t_dfs.conf ] ; then sudo rm $JETSON_EASY_FOLDER/l4t_dfs.conf ; fi
        # Store jetson_clock configuration
        sudo $HOME/jetson_clocks.sh --store $JETSON_EASY_FOLDER/l4t_dfs.conf    
        # if Jetson TX2 change type of performance
        if [ $JETSON_BOARD == "TX2" ] || [ $JETSON_BOARD == "iTX2" ]
        then
            echo "TX2 Change config"
        fi
        # Launch ./jetson_clock.sh
        sudo $HOME/jetson_clocks.sh
        # Write a file to check the system has running
        sudo touch /tmp/jetson_performance_run
    else
        echo "Service has running"
    fi
}

stop()
{
    # restore jetson_clock configuration
    sudo $HOME/jetson_clocks.sh --restore $JETSON_EASY_FOLDER/l4t_dfs.conf 
    # Delete the configuration
    sudo rm $JETSON_EASY_FOLDER/l4t_dfs.conf 
    # Write a file to check the system has running
    sudo rm /tmp/jetson_performance_run
    
    echo "STOP"
}

finstall()
{
    # installing script
    echo "Install"
}

uninstall()
{
    # Uninstalling script
    echo "Uninstall"
}

case "$1" in 
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    status)
        status
        ;;
    install)
        finstall
        ;;
    uninstall)
        uninstall
        ;;
    *)
        if [ $JETSON_BOARD == "TX2" ] || [ $JETSON_BOARD == "TX2" ]
        then
            echo "Usage: $0 [options] [type]"
        else
            echo "Usage: $0 [options]"
        fi
        echo "  options,"
        echo "  --start      |"
        echo "  --stop       |"
        echo "  --status     |"
        echo "  --restart    |"
        echo "  --install    |"
        echo "  --uninstall  |"
esac

exit 0 
