# Jetson stats
[![PyPI - Downloads](https://img.shields.io/pypi/dw/jetson-stats.svg)](https://pypistats.org/packages/jetson-stats) [![PyPI version](https://badge.fury.io/py/jetson-stats.svg)](https://badge.fury.io/py/jetson-stats) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jetson-stats.svg)](https://www.python.org/) [![PyPI - Format](https://img.shields.io/pypi/format/jetson-stats.svg)](https://pypi.org/project/jetson-stats/)

![Build](https://github.com/rbonghi/jetson_stats/workflows/Build/badge.svg) ![Docs](https://github.com/rbonghi/jetson_stats/workflows/Docs/badge.svg) ![Publish](https://github.com/rbonghi/jetson_stats/workflows/Publish/badge.svg)

**jetson-stats** is a package to **monitoring** and **control** your [NVIDIA Jetson][NVIDIA Jetson] [Nano, Xavier, TX2i, TX2, TX1] embedded board. When you install jetson-stats are included:
* [jtop](#jtop)
* [jetson_config](#jetson_config)
* [jetson_release](#jetson_release)
* [jetson_variables](#jetson_variables)

Read the [Wiki](https://github.com/rbonghi/jetson_stat/wiki) for more detailed information or read the package [documentation](https://rbonghi.github.io/jetson_stats).

## Install

```elm
sudo -H pip install -U jetson-stats
```
**🚀 That's it! 🚀** 

_PS: Don't forget to **reboot** your board_

**You can run jtop in your python script [read here][library]**

## [**jtop**][jtop] 
It is a system monitoring utility that runs on the terminal and see and **control** realtime the status of your [NVIDIA Jetson][NVIDIA Jetson]. CPU, RAM, GPU status and frequency and other...

The prompt interface will be show like this image:
![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jtop.gif)

You can run the jtop with (Suggested to run with **sudo**)
```elm
sudo jtop
```
Other options are availables with `-h` option:
```console
nvidia@jetson-nano:~/$ sudo jtop -h
usage: jtop [-h] [-r REFRESH] [--debug] [--page PAGE] [--restore] [-v]

jtop is system monitoring utility and runs on terminal

optional arguments:
  -h, --help     show this help message and exit
  -r REFRESH     refresh interval
  --debug        Run with debug logger
  --page PAGE    Open fix page
  --restore      Reset Jetson configuration
  -v, --version  show program's version number and exit
```
### Pages
**jtop** have four different pages to control your NVIDIA Jetson:
1. **ALL** Are collected all information about your board: CPUs status, Memory, *GPU*, disk, fan and all status about jetson_clocks, NVPmodel and other
2. **GPU** A real time GPU history about your NVIDIA Jetson
2. **MEM** A real time Memory chart and swap monitor
3. **CTRL** Enable/Disable **jetson_clocks**, **nvpmodel** or **fan** directly from here
4. **INFO** All information about libraries, CUDA, Serial Number, interfaces, ...
### Controls
To control the your NVIDIA Jetson are available this keyboard commands:

In page **3 MEM**:
* **c** Clear cache
* **h** Enable/Disable extra swap
* **+** and **-** Increase and decrease swap size

In page **4 CTRL**:
* **a** Start/Stop jetson_clocks service (Note: jetson_clocks start only after 60s from up time)
* **e** Enable/Disable jetson_clocks on board boot
* **+** and **-** Increase and decrease the NVPmodel
* **f** Manual/jetson_clocks mode for your fan
* **p** and **m** Increase and decrease the Fan speed

## [**jetson_config**][jetson_config]

Check _jetson-stats_ **health**, enable/disable **desktop**, enable/disable **jetson_clocks**, improve the performance of your **wifi** are available only in one click using **jetson_config**

![jetson_config](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_config.png)
## [**jetson_release**][jetson_release]
The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetso_release.png)
## [**jetson_variables**][jetson_variables]
This script generate the easy environment variables to know which is your Hardware version of the Jetson and which Jetpack you have already installed

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_env.png)

[library]: https://github.com/rbonghi/jetson_stats/wiki/library
[jtop]: https://github.com/rbonghi/jetson_stats/wiki/jtop
[jetson_config]: https://github.com/rbonghi/jetson_stats/wiki/jetson_config
[jetson_variables]: https://github.com/rbonghi/jetson_stats/wiki/jetson_variables
[jetson_release]: https://github.com/rbonghi/jetson_stats/wiki/jetson_release
[jetson_performance]: https://github.com/rbonghi/jetson_stats/wiki/jetson_performance
[jetson_docker]: https://github.com/rbonghi/jetson_stats/wiki/jetson_docker
[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: http://www.nvidia.com/object/embedded-systems-dev-kits-modules.html
