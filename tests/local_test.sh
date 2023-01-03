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

bold=`tput bold`
red=`tput setaf 1`
green=`tput setaf 2`
yellow=`tput setaf 3`
blue=`tput setaf 4`
reset=`tput sgr0`


usage()
{
    if [ "$1" != "" ]; then
        echo "${red}$1${reset}"
    fi
    
    echo "Jetson_stats tox local test. USE ONLY IN A TEST DESKTOP MACHINE!"
    echo "Usage:"
    echo "$0 [options]"
    echo "options,"
    echo "   -h|--help             | This help"
    echo "   --debug [PYHTON]      | Debug a specific python version, example PYTHON=3.9"
    echo "  -py|--python [PYHTON]  | Set a specific python version, example PYTHON=3.9"
    echo "  --only-run             | Run tox without build the docker image"
    
}

main()
{
    local DOCKER_BUILD=true
    local PYTHON_LIST="2.7 3.6 3.8 3.9 3.10"
    local PYTHON_DEBUG=""
    
    # Decode all information from startup
    while [ -n "$1" ]; do
        case "$1" in
            -h|--help)
                # Load help
                usage
                exit 0
            ;;
            --debug)
                PYTHON_DEBUG=$2
                shift 1
            ;;
            -py|--python)
                PYTHON_LIST=$2
                shift 1
            ;;
            --only-run)
                DOCKER_BUILD=false
            ;;
            *)
                usage "[ERROR] Unknown option: $1"
                exit 1
            ;;
        esac
        shift 1
    done
    
    if $DOCKER_BUILD ; then
        # Build all images
        for PYTHON_VERSION in $PYTHON_LIST; do
            echo "- ${green}Build Dockerfile image with python:${bold}$PYTHON_VERSION${reset}"
            docker build -t rbonghi/jetson-stats:tox-py$PYTHON_VERSION --build-arg "PYTHON_VERSION=$PYTHON_VERSION" -f tests/Dockerfile.tox . || { echo "${red}docker build failure!${reset}"; exit 1; }
        done
    fi

    if [ ! -z "$PYTHON_DEBUG" ] ; then
        echo "- ${yellow}Debug Image with python:${bold}$PYTHON_DEBUG${reset}"
        docker run -v $HOME/jetson_stats:/jetson_stats -it --rm --entrypoint bash rbonghi/jetson-stats:tox-py$PYTHON_DEBUG
        exit 0
    fi
    
    # Run all images
    for PYTHON_VERSION in $PYTHON_LIST; do
        echo "- ${green}Run Image and test with python:${bold}$PYTHON_VERSION${reset}"
        docker run --rm -t rbonghi/jetson-stats:tox-py$PYTHON_VERSION -e py$PYTHON_VERSION || { echo "${red}Failure TOX $PYTHON_VERSION!${reset}"; exit 1; }
    done
}

main $@
exit 0

#EOF
