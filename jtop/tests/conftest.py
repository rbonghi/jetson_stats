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

import os
import shutil
import pytest
from ..service import JtopServer
from ..core import JtopException
# pytest fixture reference
# https://docs.pytest.org/en/stable/fixture.html

FAKE_DIRECTORY = "/fake_sys"


def install_cpu():
    path_cpu = os.path.join(FAKE_DIRECTORY, "devices/system/cpu")
    # Build a list of fake CPU
    file_proc_stat = "cpu  26716126 25174 7198445 948399047 900582 0 354519 0 0 0\n"
    for cpu_num in range(4):
        file_proc_stat += "cpu{num} 1673575 1889 461134 59280326 55795 0 10322 0 0 0\n".format(num=cpu_num)
        # Build a fake folder
        cpu_path = os.path.join(path_cpu, "cpu{num}".format(num=cpu_num), "cpufreq")
        if not os.path.isdir(cpu_path):
            print('The directory {path} is not present. Creating a new one..'.format(path=cpu_path))
            os.makedirs(cpu_path)
        # Fake freq_cpu
        open(os.path.join(cpu_path, "scaling_governor"), "w").write("test_cpu")
        open(os.path.join(cpu_path, "scaling_min_freq"), "w").write("1000")
        open(os.path.join(cpu_path, "scaling_max_freq"), "w").write("1000")
        open(os.path.join(cpu_path, "scaling_cur_freq"), "w").write("1000")
        open(os.path.join(cpu_path, "cpuinfo_min_freq"), "w").write("1000")
        open(os.path.join(cpu_path, "cpuinfo_max_freq"), "w").write("1000")
        open(os.path.join(cpu_path, "cpuinfo_cur_freq"), "w").write("1000")
    file_proc_stat += "intr 1183148227 0 158138519 160761681 0 0 0 21819776 0 0 0 0 0 0 671322431\n"
    file_proc_stat += "ctxt 1028840383\n"
    file_proc_stat += "btime 1674644431\n"
    file_proc_stat += "processes 30001646\n"
    file_proc_stat += "procs_running 1\n"
    file_proc_stat += "procs_blocked 0\n"
    file_proc_stat += "softirq 1314597723 23996821 482246074 121 7508149 802592 110 476 600432457 4439 199606484\n"
    # Write fake /proc/stat
    proc_stat_file = os.path.join(FAKE_DIRECTORY, "stat")
    print("Write a fake /proc/stat in {file}".format(file=proc_stat_file))
    open(proc_stat_file, "w").write(file_proc_stat)


def install_igpu():
    path_igpu = os.path.join(FAKE_DIRECTORY, "devices/platform", "10101010.gpu")
    # Build full file
    path_igpu_device = os.path.join(FAKE_DIRECTORY, "devices/platform", "10101010.gpu", "device/of_node")
    print("Installing GPU in {path}".format(path=path_igpu_device))
    if not os.path.isdir(path_igpu_device):
        print('The directory {path} is not present. Creating a new one..'.format(path=path_igpu_device))
        os.makedirs(path_igpu_device)
    # Link file
    path_dev_freq = os.path.join(FAKE_DIRECTORY, "class/devfreq")
    if not os.path.isdir(path_dev_freq):
        print('The directory {path} is not present. Creating a new one..'.format(path=path_dev_freq))
        os.makedirs(path_dev_freq)
    os.symlink(path_igpu, os.path.join(path_dev_freq, "10101010.gpu"))
    # Write fake name
    open(os.path.join(path_igpu_device, "name"), "w").write("test_gpu")


def install_fan():
    path_fan = os.path.join(FAKE_DIRECTORY, "class/hwmon", "hwmon27")
    print("Installing Fan in {path}".format(path=path_fan))
    if not os.path.isdir(path_fan):
        print('The directory {path} is not present. Creating a new one..'.format(path=path_fan))
        os.makedirs(path_fan)
    # Build now a fake folder
    open(os.path.join(path_fan, "pwm1"), "w").write("0")
    open(os.path.join(path_fan, "pwm2"), "w").write("0")
    open(os.path.join(path_fan, "name"), "w").write("test_fan")
    # Make a fake rpm fan
    path_rpm = os.path.join(FAKE_DIRECTORY, "class/hwmon", "hwmon32")
    if not os.path.isdir(path_rpm):
        print('The directory {path} is not present. Creating a new one..'.format(path=path_rpm))
        os.makedirs(path_rpm)
    open(os.path.join(path_rpm, "rpm"), "w").write("1000")
    open(os.path.join(path_rpm, "name"), "w").write("test_rpm")


def install_nvpmodel():
    if not os.path.exists('/usr/bin/nvpmodel'):
        shutil.copy('tests/nvpmodel', '/usr/bin/nvpmodel')
        print('Copied test/nvpmodel')
    else:
        print('/usr/bin/nvpmodel already exists')


def install_jetson_clocks():
    if not os.path.exists('/usr/bin/jetson_clocks'):
        shutil.copy('tests/jetson_clocks', '/usr/bin/jetson_clocks')
        print('Copied test/jetson_clocks')
    else:
        print('/usr/bin/jetson_clocks already exists')


def empty_func():
    pass


OPTIONS = {
    'igpu': install_igpu,
    'fan': install_fan,
    'nvpmodel': install_nvpmodel,
    'jetson_clocks': install_jetson_clocks,
}


def clan_all_folder():
    if os.path.isdir(FAKE_DIRECTORY):
        print('Fake directory existing. Removing')
        shutil.rmtree(FAKE_DIRECTORY)
    # Clean nvpmodel
    if os.path.isfile('/usr/bin/nvpmodel'):
        print('Removing nvpmodel')
        os.remove('/usr/bin/nvpmodel')
    if os.path.isfile('/etc/nvpmodel.conf'):
        print('Removing /etc/nvpmodel.conf')
        os.remove('/etc/nvpmodel.conf')
    # Clean jetson_clocks
    if os.path.isfile('/usr/bin/jetson_clocks'):
        print('Removing jetson_clocks')
        os.remove('/usr/bin/jetson_clocks')
    if os.path.isfile('/tmp/nvp_model_test'):
        print('Removing /tmp/nvp_model_test')
        os.remove('/tmp/nvp_model_test')


@pytest.fixture
def setup_jtop_server(request):
    params = request.param
    # Find functions to load
    print("Start initialization test")
    clan_all_folder()
    # Install fake cpu
    # install_cpu()
    # Install all functions
    for param in params:
        print("Install function \"{param}\"".format(param=param))
        function = OPTIONS.get(param, empty_func)
        function()
    # Start jtop
    print("Starting jtop service")
    jtop_server = JtopServer(force=True)
    try:
        jtop_server.start()
    except JtopException as e:
        print(e)
        jtop_server.remove_files()
    # Check if is alive
    assert jtop_server.is_alive()
    # Pass param for test
    yield params
    # Close server
    jtop_server.close()
    # Teardown code here
    print("Close jtop service")
    # Clean test folder
    clan_all_folder()
# EOF
