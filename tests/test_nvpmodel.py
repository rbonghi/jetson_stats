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

from jtop import NVPmodel


def test_initialization():
    # Test board not in list
    nvp = NVPmodel("NotInListBoard")
    assert isinstance(nvp.modes, list)
    # Test board in list
    nvp = NVPmodel("NO-BOARD")
    assert isinstance(nvp.modes, list)


def test_nvp_good():
    # Initialize NVPmodel
    nvp = NVPmodel("NO-BOARD")
    status = nvp.status
    # Check result is a dictionary
    assert isinstance(status, dict)
    # Chek values
    assert "Name" in status
    assert status["Name"] == "Test mode"


def test_nvp_wrong():
    # Initialize NVPmodel
    nvp = NVPmodel("NotInListBoard")
    status = nvp.status
    # Check result is a dictionary
    assert isinstance(status, dict)
    # Chek values
    if not status:
        assert True
    else:
        assert False
# EOF
