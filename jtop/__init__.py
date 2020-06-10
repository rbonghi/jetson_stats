# -*- coding: UTF-8 -*-
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

# flake8: noqa

from .jtop import jtop, import_jetson_variables
# Import extra controllers
from .core import Tegrastats
from .core import Fan
from .core import NVPmodel
from .core import JetsonClocks
# Import os variable importer
from .core import StatusObserver

__author__ = "Raffaello Bonghi <raffaello@rnext.it>"
# Version package
# https://packaging.python.org/guides/distributing-packages-using-setuptools/#choosing-a-versioning-scheme
__version__ = "2.5.0rc1"
# EOF
