#!/usr/bin/env python
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


from jtop import jtop
import socket
import json
import argparse

parser = argparse.ArgumentParser(description='Simple Tegrastats server.')

# Standard loopback interface address (localhost)
parser.add_argument('--host', action="store", dest="host", default="127.0.0.1")

# Port to listen on (non-privileged ports are > 1023)
parser.add_argument('--port', action="store", dest="port", type=int, default=65432)

# Optional argument to return message in a valid HTTP response
parser.add_argument('--http', action="store_true")

args = parser.parse_args()

if __name__ == "__main__":

    print("Simple Tegrastats server")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((args.host, args.port))
    print("Open server jtop to {}:{}".format(args.host, args.port))
    sock.listen(1)

    with jtop() as jetson:
        try:
            while True:
                # Wait socket request
                conn, addr = sock.accept()
                print("Connected to {}".format(conn))
                # Read and convert in JSON the jetson stats
                stats = json.dumps(jetson.stats)
                # Send by socket
                if args.http:
                    message = "HTTP/1.1 200 OK\r\nHost: {host}:{port}\r\nContent-Type: application/json\r\nContent-Length: {length}\r\n\r\n{stats}"
                    conn.send(message.format(host=args.host, port=args.port, length=len(stats), stats=stats.encode()))
                else:
                    conn.send(stats.encode())
                # Close connection
                conn.close()
        except Exception:
            sock.close()
# EOF
