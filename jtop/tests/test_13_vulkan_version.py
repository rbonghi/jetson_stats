# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2026 Raffaello Bonghi.
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

import pytest
from ..core.jetson_libraries import get_vulkan_version

# vulkaninfo on a Jetson AGX Thor (L4T 39.2.0)
VULKANINFO_THOR = """==========
VULKANINFO
==========

Vulkan Instance Version: 1.4.321

GPU0:
VkPhysicalDeviceProperties:
---------------------------
\tapiVersion        = 1.4.329 (4211017)
\tdriverVersion     = 595.78.0.0 (2496888832)
\tvendorID          = 0x10de
\tdeviceType        = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
\tdeviceName        = NVIDIA Thor
"""

# Older vulkaninfo on a Jetson Nano, from #509
VULKANINFO_NANO = """==========
VULKANINFO
==========

Vulkan Instance Version: 1.3.204

GPU0:
VkPhysicalDeviceProperties:
---------------------------
    apiVersion        = 4198485 (1.1.85)
    driverVersion     = 134266944 (0x800c040)
    vendorID          = 0x10de
    deviceType        = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
    deviceName        = NVIDIA Tegra X1 (nvgpu)
"""

VULKANINFO_NO_GPU = """==========
VULKANINFO
==========

Vulkan Instance Version: 1.3.204
"""


@pytest.mark.parametrize("output,version", [
    (VULKANINFO_THOR, "1.4.329"),
    (VULKANINFO_NANO, "1.1.85"),
    (VULKANINFO_NO_GPU, "1.3.204"),
    ("", None),
])
def test_vulkan_version(output, version):
    assert get_vulkan_version(output.splitlines()) == version
# EOF
