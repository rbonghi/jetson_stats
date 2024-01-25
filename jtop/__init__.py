# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
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

from .core.exceptions import JtopException
from .core.gpu import GPU
from .core.memory import Memory
from .core.fan import Fan
from .core.jetson_clocks import JetsonClocks
from .core.nvpmodel import NVPModel
from .jtop import jtop

__author__ = "Raffaello Bonghi"
__email__ = "raffaello@rnext.it"
__cr__ = "(c) 2024, RB"
__copyright__ = "(c) 2024, Raffaello Bonghi"
# Version package
# https://packaging.python.org/guides/distributing-packages-using-setuptools/#choosing-a-versioning-scheme
__version__ = "4.2.6"
# EOF
