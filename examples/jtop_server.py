#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (C) 2019, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
                    conn.send("HTTP/1.1 200 OK\nContent-Type: application/json\n\n" + stats.encode())
                else:
                    conn.send(stats.encode())
                # Close connection
                conn.close()
        except Exception:
            sock.close()
# EOF
