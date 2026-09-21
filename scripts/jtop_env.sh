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

# THIS SCRIPT MUST HAVE .SH !

# Load JETSON environment variables
# Export variables to be loaded on bash script
# https://blog.tintoy.io/2017/06/exporting-environment-variables-from-python-to-bash/
JETSON_VARIABLE=""
JETSON_PYTHON_NAME=""

# Prefer uv jtop venv's Python installation
for PYTHON in \
    "$HOME/.local/share/jtop/bin/python" \
    "$HOME/.local/share/jtop/bin/python3" \
    python3 \
    python
do
    # For absolute paths, make sure the interpreter exists and is executable.
    # For command names, make sure they are in PATH.
    case "$PYTHON" in
        /*)
            [ -x "$PYTHON" ] || continue
            ;;
        *)
            command -v "$PYTHON" >/dev/null 2>&1 || continue
            ;;
    esac

    JETSON_VARIABLE=$("$PYTHON" -c \
        "import jtop; print(jtop.__path__[0])" 2>/dev/null)

    if [ -n "$JETSON_VARIABLE" ]; then
        JETSON_PYTHON_NAME="$PYTHON"
        break
    fi
done

# Load variables only if not empty the variable
if [ -n "$JETSON_VARIABLE" ]; then
    eval "$("$JETSON_PYTHON_NAME" -m jtop.core.jetson_variables)"
fi

# EOF
