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

# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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

JETSON_STATS_FOLDER="/usr/local/jetson_stats"
# Load JETSON environment variables:
# Not required jetson_variables at this time
# . $JETSON_STATS_FOLDER/jetson_variables

JETSON_PERFORMANCE_WAIT_TIME=60
JETSON_PERFORMANCE_CHECK_FILE=/tmp/jetson_performance_run
JETSON_CONFIG_FOLDER="/tmp"
JETSON_FAN_CONFIG="$JETSON_STATS_FOLDER/fan_config"

if [ -f /usr/bin/jetson_clocks ] ; then
    JETSON_CLOCK_SCRIPT=/usr/bin/jetson_clocks
elif [ -f /home/nvidia/jetson_clocks.sh ] ; then
    JETSON_CLOCK_SCRIPT=/home/nvidia/jetson_clocks.sh
else
    echo "No jetson_clock script is availble in this board"
    exit 1
fi

set_fan_speed()
{
    local FAN_PATH=$1
    local FAN_TYPE=$(sed '1q;d' $JETSON_FAN_CONFIG)
    if [ ! -z "$FAN_TYPE" ] ; then
        echo "Set fan: $FAN_TYPE"
        # Set speed only if FAN_TYPE is MANUAL
        if [ $FAN_TYPE = "MANUAL" ] ; then
            # Enable temperature control
            echo "1" > "$FAN_PATH/temp_control"
            # Load speed fan
            local FAN_SPEED=$(sed '2q;d' $JETSON_FAN_CONFIG)
            # Setup fan speed
            if [ ! -z "$FAN_SPEED" ] ; then
                echo "Set fan speed: $FAN_SPEED"
                # Set fan speed
                if [ -f "$FAN_PATH/target_pwm" ] ; then
                    echo "$FAN_SPEED" > "$FAN_PATH/target_pwm"
                fi
            fi
        fi
    fi
}

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
        echo "Service jetson_clock stats"
        # Configure the Jetson FAN
        if [ -f $JETSON_FAN_CONFIG ] ; then
            echo "Load FAN configuration"
            # Setup fan speed and type control
            if [ -d "/sys/kernel/debug/tegra_fan" ] ; then
                set_fan_speed "/sys/kernel/debug/tegra_fan"
            elif [ -d "/sys/devices/pwm-fan" ] ; then
                set_fan_speed "/sys/devices/pwm-fan"
            fi
        fi
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

    # Configure the Jetson FAN
    if [ -f $JETSON_FAN_CONFIG ] ; then
        echo "Load FAN configuration"
        # Setup fan speed and type control
        if [ -d "/sys/kernel/debug/tegra_fan" ] ; then
            set_fan_speed "/sys/kernel/debug/tegra_fan"
        elif [ -d "/sys/devices/pwm-fan" ] ; then
            set_fan_speed "/sys/devices/pwm-fan"
        fi
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
