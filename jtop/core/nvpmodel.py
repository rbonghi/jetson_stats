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

# Logging
import logging
# Launch command
import subprocess as sp

# Create logger for jplotlib
logger = logging.getLogger(__name__)


class NVPmodel():
    """
        This controller read the status from your NVIDIA Jetson and you can control
        performance and status.
        It is available for NVIDIA Jetson TX2, Jetson AGX Xavier, Jetson Nano
        Boards reference:
        * TX2: https://www.jetsonhacks.com/2017/03/25/nvpmodel-nvidia-jetson-tx2-development-kit/
        * AGX Xavier: https://www.jetsonhacks.com/2018/10/07/nvpmodel-nvidia-jetson-agx-xavier-developer-kit/
        * Nano: https://www.jetsonhacks.com/2019/04/10/jetson-nano-use-more-power/
    """
    BOARDS = {"NO-BOARD": [{"Name": "Test mode"}],
              "TX2": [{"Name": 'Max-N'},
                      {"Name": 'Max-Q'},
                      {"Name": 'Max-P Core-All'},
                      {"Name": 'Max-P ARM'},
                      {"Name": 'Max-P Denver'}],
              "Xavier": [{"Name": 'Max-N', "Power": 'N/A'},
                         {"Name": 'Mode-10W', "Power": '10W'},
                         {"Name": 'Mode-15W', "Power": '15W'},
                         {"Name": 'Mode-30W-All', "Power": '30W'},
                         {"Name": 'Mode-30W-6CORE', "Power": '30W'},
                         {"Name": 'Mode-30W-4CORE', "Power": '30W'},
                         {"Name": 'Mode-30W-2CORE', "Power": '30W'}],
              "NANO": [{"Name": 'Max-N', "Power": '20W'},
                       {"Name": 'Mode-1', "Power": '5W'}]}

    def __init__(self, board):
        self.board = ""
        # Find name board from board list
        for name in NVPmodel.BOARDS.keys():
            if board.lower() in name.lower():
                self.board = name
                logger.info("Board found: {}".format(self.board))
                break
        if self.board:
            logger.info("This board {} does not have NVP Model".format(self.board))

    def modes(self):
        if self.board:
            return NVPmodel.BOARDS[self.board]
        else:
            return {}

    def set(self, level):
        """ Set nvpmodel to a new status """
        if self.board:
            try:
                sp.Popen(['nvpmodel', '-m', level], stdout=sp.PIPE)
                return True
            except OSError:
                logger.info("NVP Model does not exist")
        else:
            return False

    @property
    def status(self):
        """ Read nvpmodel to know the status of the board """
        if self.board:
            try:
                nvpmodel_p = sp.Popen(['nvpmodel', '-q'], stdout=sp.PIPE)
                out, _ = nvpmodel_p.communicate()
                # Log value
                logger.debug('nvqmodel status %s', out)
                # Decode lines and split
                lines = out.decode("utf-8").split("\n")
                # Return the mode type
                # Name mode: lines[0].split(": ")[1]
                mode_num = int(lines[1])
                return NVPmodel.BOARDS[self.board][mode_num]
            except OSError:
                logger.info("NVP Model does not exist")
        else:
            return {}
# EOF
