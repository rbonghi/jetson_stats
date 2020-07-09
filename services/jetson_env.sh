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

# Load JETSON environment variables
JTOP_VARIABLE=""
if type -P python3 >/dev/null 2>&1 ; then
    JTOP_VARIABLE=$(python3 -c "import jtop; print(jtop.__path__[0])" 2> /dev/null)
fi
if type -P python >/dev/null 2>&1 && [ -z $JTOP_VARIABLE ] ; then
    JTOP_VARIABLE=$(python -c "import jtop; print(jtop.__path__[0])" 2> /dev/null)
fi
# Load variables only if not empty the variable
if [ ! -z $JTOP_VARIABLE ] ; then
    . $JTOP_VARIABLE/jetson_variables
    . $JTOP_VARIABLE/jetson_libraries
fi
# EOF
