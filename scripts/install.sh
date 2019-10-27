#!/bin/bash
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


BIN_FOLDER="/usr/local/bin"

# Load jetson_variables
source scripts/jetson_variables

js_uninstall_old()
{
    local FORCE=$1
    local JETSON_FOLDER=$2
    
    # Remove jetson-docker link
    if [ -f "$BIN_FOLDER/jetson-docker" ] ; then
        echo "   * Remove OLD jetson-docker link"
        sudo rm "$BIN_FOLDER/jetson-docker"
    fi
    
    # Remove jetson_release link
    if [ -f "$BIN_FOLDER/jetson-release" ] ; then
        echo "   * Remove OLD jetson-release link"
        sudo rm "$BIN_FOLDER/jetson-release"
    fi

    # Remove jetson_release link
    if [ -f "$BIN_FOLDER/jetson-swap" ] ; then
        echo "   * Remove OLD jetson-swap link"
        sudo rm "$BIN_FOLDER/jetson-swap"
    fi
    
    if [ -f "$BIN_FOLDER/jtop" ] ; then
        echo "   * Remove jtop link"
        sudo rm "$BIN_FOLDER/jtop"
    fi
    
    # Remove /etc/jetson_easy folder
    if [ -d "/etc/jetson_easy" ] ; then
        echo "   * Remove jetson_easy folder"
        sudo rm -R "/etc/jetson_easy"
    fi
}

js_uninstall()
{
    local FORCE=$1
    local JETSON_FOLDER=$2

    # Remove fan service from /etc/init.d
    if [ -f "/etc/systemd/system/jetson_fan.service" ] ; then
        # Disable service
        echo "   * Disable service from /etc/systemd/system"
        sudo systemctl disable jetson_fan.service
        # Remove service in list
        echo "   * Remove the service from /etc/systemd/system"
        sudo rm "/etc/systemd/system/jetson_fan.service"
        # Update service list
        echo "   * Reload services list"
        sudo systemctl daemon-reload
    fi
    
    # Remove jetson_performance service from /etc/init.d
    if [ -f "/etc/systemd/system/jetson_performance.service" ] ; then
        # Uninstall the service
        if [ $(systemctl is-active jetson_performance.service) = "active" ] ; then
            tput setaf 1
            echo "   * Stop and jetson_performance service"
            tput sgr0
            # Stop the service
            sudo systemctl stop jetson_performance.service
        fi
        # Disable the service
        echo "   * Disable service from /etc/systemd/system"
        sudo systemctl disable jetson_performance.service
        # Remove service in list
        echo "   * Remove the service from /etc/systemd/system"
        sudo rm "/etc/systemd/system/jetson_performance.service"
        # Update service list
        echo "   * Reload services list"
        sudo systemctl daemon-reload
    fi

    # Remove fan configuration
    if [ -f $JETSON_FOLDER/fan_config ] ; then
        echo "   * Remove fan_config from $JETSON_FOLDER"
        sudo rm $JETSON_FOLDER/fan_config
    fi
    
    # Remove configuration
    if [ -f $JETSON_FOLDER/l4t_dfs.conf ] ; then
        echo "   * Remove l4t_dfs.conf from $JETSON_FOLDER"
        sudo rm $JETSON_FOLDER/l4t_dfs.conf
    fi
    
    # Remove jetson_release link
    if [ -f "$BIN_FOLDER/jetson_release" ] ; then
        echo "   * Remove jetson_release link"
        sudo rm "$BIN_FOLDER/jetson_release"
    fi

    # Remove jetson_release link
    if [ -f "$BIN_FOLDER/jetson_swap" ] ; then
        echo "   * Remove jetson_swap link"
        sudo rm "$BIN_FOLDER/jetson_swap"
    fi
    
    # Remove jetson-docker link
    if [ -f "$BIN_FOLDER/jetson_docker" ] ; then
        echo "   * Remove jetson_docker link"
        sudo rm "$BIN_FOLDER/jetson_docker"
    fi

    # Remove folder
    if [ -d "$JETSON_FOLDER" ] ; then
        echo "   * Remove $JETSON_FOLDER folder"
        sudo rm -R $JETSON_FOLDER
    fi
}

js_install()
{
    local FORCE=$1
    local JETSON_FOLDER=$2
    
    echo "   * Make folder $JETSON_FOLDER"
    sudo mkdir -p "$JETSON_FOLDER"
    
    echo "   * Copy scrips in $JETSON_FOLDER"
    sudo cp "scripts/jetson_variables" "$JETSON_FOLDER/jetson_variables"
    sudo cp "scripts/jetson_performance.sh" "$JETSON_FOLDER/jetson_performance.sh"
    sudo cp "scripts/jetson_swap" "$JETSON_FOLDER/jetson_swap"
    sudo cp "scripts/jetson_release" "$JETSON_FOLDER/jetson_release"
    sudo cp "scripts/jetson_fan.sh" "$JETSON_FOLDER/jetson_fan.sh"
    
    echo "   * Copy jetson_env.sh in /etc/profile.d/"
    sudo cp "scripts/jetson_env.sh" "/etc/profile.d/jetson_env.sh"
    
    echo "   * Copy jetson_performance.service in service list"
    sudo cp "scripts/jetson_performance.service" "/etc/systemd/system/jetson_performance.service"

    echo "   * Copy jetson_fan.service in service list"
    sudo cp "scripts/jetson_fan.service" "/etc/systemd/system/jetson_fan.service"

    if [ ! -f $BIN_FOLDER/jetson_swap ] ; then
        echo "   * Link jetson_swap in $BIN_FOLDER"
        sudo ln -s $JETSON_FOLDER/jetson_swap $BIN_FOLDER/jetson_swap
    fi
    if [ ! -f $BIN_FOLDER/jetson_release ] ; then
        echo "   * Link jetson_release in $BIN_FOLDER"
        sudo ln -s $JETSON_FOLDER/jetson_release $BIN_FOLDER/jetson_release
    fi
    
    # Install jetson_docker only for Jetpack before L4T 32
    if [ $JETSON_L4T_RELEASE -lt 32 ]; then
        echo "   * Copy jetson_docker in $JETSON_FOLDER for L4T=$JETSON_L4T_RELEASE"
        sudo cp "scripts/jetson_docker" "$JETSON_FOLDER/jetson_docker"
        
        if [ ! -f $BIN_FOLDER/jetson_docker ] ; then
            echo "   * Link jetson_docker in $BIN_FOLDER for L4T=$JETSON_L4T_RELEASE"
            sudo ln -s $JETSON_FOLDER/jetson_docker $BIN_FOLDER/jetson_docker
        fi
    fi
    
    # Update service list
    echo "   * Reload services list"
    sudo systemctl daemon-reload

    # Enable jetson fan at startup
    echo "   * Reload services list"
    sudo systemctl enable jetson_fan.service
}

js_test_uninstall()
{
    local FORCE=$1
    
    # Remove tegrastats
    if [ -f /usr/bin/tegrastats ] ; then
        echo " - Remove /usr/bin/tegrastats"
        sudo rm /usr/bin/tegrastats
    else
        echo " - /usr/bin/tegrastats does not exist"
    fi
    # Remove nvpmodel
    if [ -f /usr/bin/nvpmodel ] ; then
    echo " - Remove /usr/bin/nvpmodel"
        sudo rm /usr/bin/nvpmodel
    else
        echo " - /usr/bin/nvpmodel does not exist"
    fi
    # Remove jetson_clock
    if [ -f /usr/bin/jetson_clocks ] ; then
    echo " - Remove /usr/bin/jetson_clocks"
        sudo rm /usr/bin/jetson_clocks
    else
        echo " - /usr/bin/jetson_clocks does not exist"
    fi
}

js_test_install()
{
    local FORCE=$1
    
    # tegrastats emulator
    if [ ! -f /usr/bin/tegrastats ] || $FORCE ; then
        echo " - Copy emulation tegrastats in /usr/bin/"
        sudo cp tests/tegrastats /usr/bin/
    else
        echo " - Already exist tegrastats in /usr/bin/"
    fi
    # nvpmodel emulator
    if [ ! -f /usr/bin/nvpmodel ] || $FORCE ; then
    echo " - Copy emulation nvpmodel in /usr/bin/"
        sudo cp tests/nvpmodel /usr/bin/
    else
        echo " - Already exist nvpmodel in /usr/bin/"
    fi
    # jetson_clock
    if [ ! -f /usr/bin/jetson_clocks ] || $FORCE ; then
    echo " - Copy emulation jetson_clocks in /usr/bin/"
        sudo cp tests/jetson_clocks /usr/bin/
    else
        echo " - Already exist jetson_clocks in /usr/bin/"
    fi
}

js_pyp()
{
    local FORCE=$1
    
    echo " - Install jetson_stats"
    # Launch installer pip
    if $FORCE ; then
        sudo -H pip install -U -e .
    else
        sudo -H pip install -e .
    fi
}

js_service_auto()
{
    tput setaf 4
    echo " - Enable and start jetson_performance"
    tput sgr0
    # Enable service
    sudo systemctl enable jetson_performance.service
    # Run the service
    sudo systemctl start jetson_performance.service
}

usage()
{
	if [ "$1" != "" ]; then
    	tput setaf 1
		echo "$1"
		tput sgr0
	fi
	
    echo "Jetson_stats, Installer for nvidia top and different information modules."
    echo "Usage:"
    echo "$0 [options]"
    echo "options,"
    echo "   -h|--help    | This help"
    echo "   -s|--silent  | Run jetson_stats in silent mode"
    echo "   -f|--force   | Force install all tools"
    echo "   -i|--inst    | Change default install folder"
    echo "   -auto        | Run at start-up jetson performance"
    echo "   --uninstall  | Run the uninstaller"
    echo "   -test        | Install test files"
    echo "   -pyp         | Install this repository"
}

main()
{
    local SKIP_ASK=true
    local UNINSTALL=false
    local TEST_FILES=false
    local FORCE=false
    local SERVICE_AUTO=false
    local PYP=false
    local JETSON_FOLDER="/opt/jetson_stats"
    
	# Decode all information from startup
    while [ -n "$1" ]; do
        case "$1" in
            -h|--help)
                # Load help
                usage
                exit 0
                ;;
            -s|--silent)
                SKIP_ASK=false
                ;;
            -f|--force)
                FORCE=true
                ;;
            -i|--inst)
                JETSON_FOLDER=$2
                shift 1
                ;;
            -auto)
                SERVICE_AUTO=true
                ;;
            --uninstall)
                UNINSTALL=true
                ;;
            -test)
                TEST_FILES=true
                ;;
            -pyp)
                PYP=true
                ;;
            *)
                usage "[ERROR] Unknown option: $1"
                exit 1
            ;;
        esac
            shift 1
    done

    if [ $(basename $(pwd)) == "scripts" ] ; then
        tput setaf 1
        echo "Please run in home project"
        tput sgr0
        exit 1
    fi    

    if [[ `id -u` -ne 0 ]] ; then 
        tput setaf 1
        echo "Please run as root"
        tput sgr0
        exit 1
    fi
    
	local install_uninstall_string="install"
	if $UNINSTALL ; then
        install_uninstall_string="uninstall"
    fi
	
    while $SKIP_ASK; do
        read -p "Do you wish to $install_uninstall_string jetson_stats? [Y/n] " yn
            case $yn in
                [Yy]* ) # Break and install jetson_stats 
                        break;;
                [Nn]* ) exit;;
            * ) echo "Please answer yes or no.";;
        esac
    done
    # Show options
    tput setaf 3
    echo "RUN $install_uninstall_string jetson-stats WORKDIR $JETSON_FOLDER"
    tput sgr0
    if $FORCE ; then
        tput setaf 4
        echo "Force $install_uninstall_string"
        tput sgr0
    fi
    
    # Run installer/uninstaller
    if $UNINSTALL ; then
        # Check if uninstall TEST files
        if $TEST_FILES ; then
            js_test_uninstall $FORCE
        else
            js_uninstall_old $FORCE $JETSON_FOLDER
            js_uninstall $FORCE $JETSON_FOLDER
        fi
    else
        # Check if uninstall TEST files
        if $TEST_FILES ; then
            js_test_install $FORCE
        else
            if $PYP ; then
                # Run python installer
                js_pyp $FORCE
            else
                # Run installer
                js_install $FORCE $JETSON_FOLDER
                
                # Enable and start service
                if $SERVICE_AUTO ; then
                    js_service_auto
                fi
            fi
        fi
    fi

    tput setaf 2
    echo "DONE!"
    tput sgr0
}

main $@
exit 0

#EOF
