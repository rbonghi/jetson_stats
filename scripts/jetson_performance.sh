#!/bin/sh
# kFreeBSD do not accept scripts as interpreters, using #!/bin/sh and sourcing.
if [ true != "$INIT_D_SCRIPT_SOURCED" ] ; then
    set "$0" "$@"; INIT_D_SCRIPT_SOURCED=true . /lib/init/init-d-script
fi
### BEGIN INIT INFO
# Provides:          jetson_performance
# Required-Start:    $remote_fs $all
# Required-Stop:     
# Default-Start:     2 3 4 5
# Default-Stop:      
# Short-Description: Script to use the jetson_clock.sh like service
# Description:       Script to use the jetson_clock.sh like service and delay start up.
### END INIT INFO

# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
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

# Author: Raffaello Bonghi <raffaello@rnext.it>

# Reference:
# 1 - Maximum speed
# https://devtalk.nvidia.com/default/topic/1000657/script-for-maximum-clockspeeds-and-performence/
# 2 - 60sec delay only for release befor 28.1
# https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
# 3 - NVPModel for NVIDIA Jetson TX2
# http://www.jetsonhacks.com/2017/03/25/nvpmodel-nvidia-jetson-tx2-development-kit/
# https://devblogs.nvidia.com/jetson-tx2-delivers-twice-intelligence-edge/
# https://devblogs.nvidia.com/jetpack-doubles-jetson-inference-perf/
# 3a- NVPModel for NVIDIA Jetson Xavier
# https://www.jetsonhacks.com/2018/10/07/nvpmodel-nvidia-jetson-agx-xavier-developer-kit/
# 4- Enable/disable service
# https://askubuntu.com/questions/19320/how-to-enable-or-disable-services

 . /lib/lsb/init-functions
 . /lib/init/vars.sh

JETSON_STATS_FOLDER=/opt/jetson_stats
# Load JETSON environment variables:
. $JETSON_STATS_FOLDER/jetson_variables

JETSON_PERFORMANCE_WAIT_TIME=60
JETSON_PERFORMANCE_CHECK_FILE=/tmp/jetson_performance_run
JETSON_CONFIG_FOLDER="/tmp"

if [ -f /usr/bin/jetson_clocks ] ; then
    JETSON_CLOCK_SCRIPT=/usr/bin/jetson_clocks
elif [ -f /home/nvidia/jetson_clocks.sh ] ; then
    JETSON_CLOCK_SCRIPT=/home/nvidia/jetson_clocks.sh
else
    echo "No jetson_clock script is availble in this board"
    exit 1
fi


status()
{
    if [ -f $JETSON_PERFORMANCE_CHECK_FILE ] ; then
        echo "[Service running] jetson_clock --show:"
    else
        echo "[Service stopped] jetson_clock --show:"
    fi
    # Show status of the NVIDIA Jetson
    sudo $JETSON_CLOCK_SCRIPT --show
}

start()
{
    # Check which version is L4T is loaded
    # if is before the 28.1 require to launch jetson_clock.sh only 60sec before the boot
    # https://devtalk.nvidia.com/default/topic/1027388/jetson-tx2/jetson_clock-sh-1-minute-delay/
    # Temporary disabled to find a best way to start this service.
    # The service ondemand disabled doesn't improve the performance of the start-up
    # ----
    # Time from boot 
    local BOOT_TIME=$(cat /proc/uptime | cut -f1 -d " ")
    # Wait a minute from boot before start
    if [ $(echo $BOOT_TIME'<'$((JETSON_PERFORMANCE_WAIT_TIME+1)) | bc -l) -eq 1 ] ; then
        local TIME_TO_WAIT=$(echo $((JETSON_PERFORMANCE_WAIT_TIME+1))'-'$BOOT_TIME | bc)
        echo "Wait from boot other $TIME_TO_WAIT sec..."
        # Sleep for other time
        sleep $TIME_TO_WAIT
        echo "...done!"
    fi
    
    if [ ! -f $JETSON_PERFORMANCE_CHECK_FILE ] ; then
        # check if exist l4t_dfs.conf otherwhise delete
        if [ ! -f $JETSON_STATS_FOLDER/l4t_dfs.conf ] ; then
            echo "Store the jetson_clock.sh configuration"
            # Store jetson_clock configuration
            sudo $JETSON_CLOCK_SCRIPT --store $JETSON_STATS_FOLDER/l4t_dfs.conf
        fi
        # Launch jetson_clock
        sudo $JETSON_CLOCK_SCRIPT
        # Write a file to check the system has running
        sudo touch $JETSON_PERFORMANCE_CHECK_FILE
        echo "Service run at max performance"
    else
        echo "Service has running"
    fi
}

stop()
{
    if [ -f $JETSON_STATS_FOLDER/l4t_dfs.conf ] ; then
        # restore jetson_clock configuration
        sudo $JETSON_CLOCK_SCRIPT --restore $JETSON_STATS_FOLDER/l4t_dfs.conf
    fi
    
    # Write a file to check the system has running
    if [ -f $JETSON_PERFORMANCE_CHECK_FILE ] ; then
        sudo rm $JETSON_PERFORMANCE_CHECK_FILE
    fi
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
    *)
        echo "Usage: $0 [options] [type]"
        echo "  options,"
        echo "  start      | Run jetson_clock.sh and set the performance at max value"
        echo "  stop       | Stop the jetson_clock.sh and restore the old configuration"
        echo "  status     | Show the status of the system"
        echo "  restart    | Restart the system"
esac

exit 0 
