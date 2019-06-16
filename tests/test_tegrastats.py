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

from jtop import Tegrastats


def test_wrong_open():
    # Initialize object
    tegra = Tegrastats('wrong_path', 100, 1.0)
    try:
        # Open data
        tegra.open()
        assert False
    except Tegrastats.TegrastatsException:
        assert True


def test_open():
    # Initialize object
    tegra = Tegrastats('/usr/bin/tegrastats', 100, 1.0)
    # Open data
    tegra.open()
    # Close connection
    tegra.close()
    assert True


def check_tegra(tegra):
    # Check if is correctly written the variable
    assert "RAM" in tegra.stats
    variable = tegra.stats["RAM"]
    assert "RAM" in variable
    variable = tegra.stats["RAM"]["RAM"]
    # Check if ram["used"] is a list
    assert isinstance(variable["used"], list)
    # Check if last value is the same send
    assert variable["used"][-1] == 4722


def test_stats():
    # Load tegracontroller
    with Tegrastats('/usr/bin/tegrastats', 100, 1.0) as tegra:
        # Check tegra stats
        check_tegra(tegra)


def test_stats_callback():
    # Initialize object
    tegra = Tegrastats('/usr/bin/tegrastats', 100, 1.0)
    # Open data
    tegra.open(check_tegra)
    # Close connection
    tegra.close()
# EOF
