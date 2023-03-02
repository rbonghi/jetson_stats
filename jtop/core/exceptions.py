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


class JtopException(Exception):
    """
    raise when jtop fail. The message attached show the reason.
    """

    def __init__(self, message, errors=""):
        super(JtopException, self).__init__(message, errors)
        # Now for your custom code...
        self.message = message
        self.errors = errors

    def __repr__(self):
        return str(self.message)

    def __str__(self):
        return str(self.message)
# EOF
