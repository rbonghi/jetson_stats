#!/usr/bin/env python
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

from flask import Flask, Response
from jtop import jtop
import json

class WebService:

    def __init__(self):
        # Load Service
        self._app = Flask(__name__)
        # Register update function
        self._app.add_url_rule('/status', 'status', self.status)
        # Initialize jtop
        self._jetson = jtop()
        # start service
        self.start()

    def status(self):
        response = {}
        # Get uptime
        response['uptime'] = str(self._jetson.uptime)
        # Spin jtop
        self._jetson.ok(spin=True)
        # return data
        return Response(
            response=json.dumps(response),
            status=201,
            mimetype="application/json"
        )
        
    def start(self):
        print("Init server ...")
        # Start jtop
        self._jetson.start()
        # Start server
        self._app.run(debug=True)
        
    def stop(self):
        print("switch off server")
        # Stop jtop
        self._jetson.close()
        # Stop server
        

if __name__ == "__main__":
    # Initialize service
    service = WebService()
    service.stop()