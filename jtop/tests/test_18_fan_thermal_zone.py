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


import os

from ..core import fan as fan_mod
from ..core.fan import FanService, assign_fan_thermal_zones, get_fan_thermal_zones


class FakeConfig:
    def __init__(self, data=None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


def make_zone(root, idx, policy, cdev_types):
    zone = root / "thermal_zone{}".format(idx)
    zone.mkdir()
    (zone / "policy").write_text(policy + "\n")
    for n, ctype in enumerate(cdev_types):
        cdev = zone / "cdev{}".format(n)
        cdev.mkdir()
        (cdev / "type").write_text(ctype + "\n")
    return str(zone)


def make_service(tmp_path, profile, zones, pwm_writable=True):
    pwm = tmp_path / "pwm1"
    pwm.write_text("88\n")
    if not pwm_writable:
        pwm.chmod(0o444)
    svc = FanService.__new__(FanService)
    svc._config = FakeConfig({"fan": {"pwmfan": {"profile": profile}}})
    svc._fan_list = {"pwmfan": {"path": str(tmp_path), "pwm": [str(pwm)], "profile": ["quiet", "manual"]}}
    svc._nvfancontrol = False
    svc._thermal_zones = {"pwmfan": zones}
    return svc, pwm


def policy(zone):
    with open(os.path.join(zone, "policy")) as f:
        return f.read().strip()


PWM_FAN = {"device": "/sys/devices/platform/pwm-fan", "of_node": "/sys/firmware/devicetree/base/pwm-fan"}


def test_zone_only_with_fan_cdevs(tmp_path):
    fan_zone = make_zone(tmp_path, 0, "step_wise", ["pwm-fan", "pwm-fan"])
    make_zone(tmp_path, 1, "step_wise", ["pwm-fan", "cpufreq-cpu0"])
    assert get_fan_thermal_zones(PWM_FAN, str(tmp_path)) == [fan_zone]


def test_unreadable_zone_is_skipped(tmp_path, monkeypatch):
    good = make_zone(tmp_path, 0, "step_wise", ["pwm-fan"])
    bad = make_zone(tmp_path, 1, "step_wise", ["pwm-fan"])
    real_listdir = os.listdir

    def listdir(path):
        if path == bad:
            raise PermissionError(path)
        return real_listdir(path)
    monkeypatch.setattr(fan_mod.os, "listdir", listdir)
    assert get_fan_thermal_zones(PWM_FAN, str(tmp_path)) == [good]


def test_zone_matched_by_two_fans_is_left_alone(tmp_path):
    make_zone(tmp_path, 0, "step_wise", ["pwm-fan"])
    fans = {"pwmfan": dict(PWM_FAN), "pwmfan1": dict(PWM_FAN)}
    zones, _ = assign_fan_thermal_zones(fans, {}, str(tmp_path))
    assert zones == {}


def test_original_governor_is_saved_and_reused(tmp_path):
    zone = make_zone(tmp_path, 0, "power_allocator", ["pwm-fan"])
    fan_config = {}
    zones, changed = assign_fan_thermal_zones({"pwmfan": dict(PWM_FAN)}, fan_config, str(tmp_path))
    assert changed and zones == {"pwmfan": {zone: "power_allocator"}}
    # Next start finds the zone in user_space: restore to the saved governor, not step_wise
    with open(os.path.join(zone, "policy"), "w") as f:
        f.write("user_space\n")
    zones, changed = assign_fan_thermal_zones({"pwmfan": dict(PWM_FAN)}, fan_config, str(tmp_path))
    assert not changed and zones == {"pwmfan": {zone: "power_allocator"}}


def test_manual_speed_takes_control(tmp_path):
    zone = make_zone(tmp_path, 0, "step_wise", ["pwm-fan"])
    svc, pwm = make_service(tmp_path, "manual", {zone: "step_wise"})
    svc.set_speed("pwmfan", 100, 0)
    assert policy(zone) == "user_space"
    assert pwm.read_text() == "255"
    assert svc._config.data["fan"]["pwmfan"]["speed"] == (100, 0)


def test_speed_in_auto_profile_keeps_governor(tmp_path):
    # jtop.restore() selects the default (automatic) profile, then sets speed 0
    zone = make_zone(tmp_path, 0, "step_wise", ["pwm-fan"])
    svc, pwm = make_service(tmp_path, "quiet", {zone: "step_wise"})
    svc.set_speed("pwmfan", 0, 0)
    assert policy(zone) == "step_wise"
    assert pwm.read_text() == "0"


def test_unwritable_pwm_keeps_governor(tmp_path):
    if os.geteuid() == 0:
        return  # root can write a read-only file
    zone = make_zone(tmp_path, 0, "step_wise", ["pwm-fan"])
    svc, pwm = make_service(tmp_path, "manual", {zone: "step_wise"}, pwm_writable=False)
    svc.set_speed("pwmfan", 100, 0)
    assert policy(zone) == "step_wise"
    assert "speed" not in svc._config.data["fan"]["pwmfan"]


def test_policy_failure_rolls_back(tmp_path):
    ok_zone = make_zone(tmp_path, 0, "step_wise", ["pwm-fan"])
    missing = str(tmp_path / "thermal_zone9")  # policy cannot be read or written
    svc, pwm = make_service(tmp_path, "manual", {ok_zone: "step_wise", missing: "step_wise"})
    svc.set_speed("pwmfan", 100, 0)
    assert policy(ok_zone) == "step_wise"
    assert pwm.read_text() == "88\n"
    assert "speed" not in svc._config.data["fan"]["pwmfan"]


def test_already_active_profile_is_saved(tmp_path, monkeypatch):
    svc, _ = make_service(tmp_path, "quiet", {})
    monkeypatch.setattr(FanService, "get_profile", lambda self, name: "manual")
    assert svc.set_profile("pwmfan", "manual")
    assert svc._config.data["fan"]["pwmfan"]["profile"] == "manual"
# EOF
