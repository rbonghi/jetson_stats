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

from jtop import JetsonClocks
import time


def test_init_jc():
    # Initialize JetsonClocks
    JetsonClocks()
    assert True


def test_read_status():
    # Initialize JetsonClocks
    jc = JetsonClocks()
    assert isinstance(jc.status, str)


def test_set_start():
    # Initialize JetsonClocks
    jc = JetsonClocks()
    start = True
    # Start JetsonClocks
    jc.start = start
    # Wait a second
    time.sleep(1)
    # Check the status is the same
    assert jc.start == start
    # Check stop
    start = False
    # Start JetsonClocks
    jc.start = start
    # Wait a second
    time.sleep(1)
    # Check the status is the same
    assert jc.start == start


def test_set_enable():
    # Initialize JetsonClocks
    jc = JetsonClocks()
    new_enable = True
    # Enable JetsonClocks
    jc.enable = new_enable
    # Wait a second
    time.sleep(1)
    # Check enable is the same
    assert jc.enable == new_enable
    # Check disable
    new_enable = False
    # Disable JetsonClocks
    jc.enable = new_enable
    # Wait a second
    time.sleep(1)
    # Check enable is the same
    assert jc.enable == new_enable
# EOF
