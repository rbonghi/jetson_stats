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

usage()
{
    if [ "$1" != "" ]; then
        tput setaf 1
        echo "$1"
        tput sgr0
    fi

    echo "Jetson_stats, fake scripts. USE ONLY IN A TEST DESKTOP MACHINE!"
    echo "Usage:"
    echo "$0 [options]"
    echo "options,"
    echo "   -h|--help    | This help"
    echo "   -s|--silent  | Run jetson_stats in silent mode"
    echo "   -f|--force   | Force install all tools"
    echo "   --uninstall  | Run the uninstaller"
}

main()
{
    local SKIP_ASK=true
    local UNINSTALL=false
    local FORCE=false

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
            --uninstall)
                UNINSTALL=true
                ;;
            *)
                usage "[ERROR] Unknown option: $1"
                exit 1
            ;;
        esac
            shift 1
    done

    if [ $(basename $(pwd)) = "scripts" ] ; then
        tput setaf 1
        echo "Please run in home project"
        tput sgr0
        exit 1
    fi

    if [ `id -u` -ne 0 ] ; then
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
        read -p "Do you wish to $install_uninstall_string jetson_stats scripts? [Y/n] " yn
            case $yn in
                [Yy]* ) # Break and install jetson_stats 
                        break;;
                [Nn]* ) exit;;
            * ) echo "Please answer yes or no.";;
        esac
    done
    # Show options
    if $FORCE ; then
        tput setaf 4
        echo "Force $install_uninstall_string"
        tput sgr0
    fi

    # Run installer/uninstaller
    if $UNINSTALL ; then
        js_test_uninstall $FORCE
    else
        js_test_install $FORCE
    fi

    tput setaf 2
    echo "DONE!"
    tput sgr0
}

main $@
exit 0

#EOF
