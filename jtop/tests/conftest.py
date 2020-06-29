# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
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

import logging
import pytest
from ..service import JtopServer
# Create logger
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def jtop_server():
    logging.basicConfig(level=logging.DEBUG, filemode='w', format='%(name)s - %(levelname)s - %(message)s')
    print("Initialize jtop service")
    jtop_server = JtopServer()
    jtop_server.start(force=True)
    yield jtop_server
    status = jtop_server.close()
    print("Close jtop service {}".format(status))
# EOF
