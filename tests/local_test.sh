#!/bin/bash
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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
    echo "   --debug               | Run image"
    echo "  -py|--python [PYHTON]  | Set a specific python version, example PYTHON=3.9"
    echo "  --doc                  | Run and build ONLY the documentation"
    
}

main()
{
    local DOCKER_BUILD=true
    local DOCUMENTATION_BUILD=true
    local PYTHON_LIST="2.7 3.6 3.8 3.9 3.10 3.11"
    local PYTHON_DEBUG=false
    local DOCUMENTATION=false
    
    # Decode all information from startup
    while [ -n "$1" ]; do
        case "$1" in
            -h|--help)
                # Load help
                usage
                exit 0
            ;;
            --doc)
                DOCKER_BUILD=false
                DOCUMENTATION=true
            ;;
            --debug)
                PYTHON_DEBUG=true
                DOCUMENTATION_BUILD=false
                DOCKER_BUILD=false
            ;;
            -py|--python)
                PYTHON_LIST=$2
                DOCUMENTATION_BUILD=false
                shift 1
            ;;
            *)
                usage "[ERROR] Unknown option: $1"
                exit 1
            ;;
        esac
        shift 1
    done
    
    
    if $DOCUMENTATION_BUILD ; then
        echo "- ${green}Build and compile jetson-stats documentation with sphinx${reset}"
        docker build -t rbonghi/jetson-stats:doc -f tests/Dockerfile.sphinx . || { echo "${red}docker build failure!${reset}"; exit 1; }
    fi
    
    if $DOCKER_BUILD ; then
        # Build all images
        for PYTHON_VERSION in $PYTHON_LIST; do
            echo "- ${green}Build and test image with python:${bold}$PYTHON_VERSION${reset}"
            docker build -t rbonghi/jetson-stats:tox-py$PYTHON_VERSION --build-arg "PYTHON_VERSION=$PYTHON_VERSION" -f tests/Dockerfile.tox . || { echo "${red}docker build failure!${reset}"; exit 1; }
        done
    fi
    
    if $PYTHON_DEBUG ; then
        if $DOCUMENTATION ; then
            echo "- ${yellow}Debug documentation image${reset}"
            docker run -v $(pwd):/jetson_stats -it --rm rbonghi/jetson-stats:doc
        else
            PYTHON_VERSION=$PYTHON_LIST
            echo "- ${yellow}Debug Image with python:${bold}$PYTHON_VERSION${reset}"
            docker run -v $(pwd):/jetson_stats -it --rm rbonghi/jetson-stats:tox-py$PYTHON_VERSION
        fi
    fi
    
}

main $@
exit 0

#EOF
