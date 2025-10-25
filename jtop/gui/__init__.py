# -*- coding: UTF-8 -*-
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

# flake8: noqa

from .jtopguiconfig import JTOPCONFIG
from .jtopgui import JTOPGUI, Page
from .pall import ALL
from .pcpu import CPU
from .pengine import ENGINE, engine_model
from .pmem import MEM
from .pcontrol import CTRL
from .pinfo import INFO
from jtop.core.hw_detect import is_thor

try:
    from jtop.core.hw_detect import is_thor
    _is_thor = is_thor()
except Exception:
    try:
        from jtop.core.thor_power import devfreq_nodes
        _is_thor = bool(devfreq_nodes())
    except Exception:
        _is_thor = False
try:
    if _is_thor:
        from .pgpu_thor import GPU
    else:
        from .pgpu import GPU

except Exception:
    from .pgpu import GPU

if 'GPU' not in globals():
    from .pgpu import GPU


# EOF
