# Jetson stats
[![PyPI - Downloads](https://img.shields.io/pypi/dw/jetson-stats.svg)](https://pypistats.org/packages/jetson-stats) [![PyPI version](https://badge.fury.io/py/jetson-stats.svg)](https://badge.fury.io/py/jetson-stats) [![Build Status](https://travis-ci.org/rbonghi/jetson_stats.svg?branch=master)](https://travis-ci.org/rbonghi/jetson_stats) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jetson-stats.svg)](https://www.python.org/) [![PyPI - Format](https://img.shields.io/pypi/format/jetson-stats.svg)](https://pypi.org/project/jetson-stats/)

**jetson-stats** is a package to **monitoring** and **control** your [NVIDIA Jetson][NVIDIA Jetson] [Nano, Xavier, TX2i, TX2, TX1] embedded board. When you install jetson-stats are included:
* [jtop](#jtop)
* [jetson_release](#jetson_release)
* [jetson_variables](#jetson_variables)

Read the [Wiki](https://github.com/rbonghi/jetson_stat/wiki) for more detailed information

## Install

```elm
sudo -H pip install jetson-stats
```
**🚀 That's it! 🚀** 

There are not require other information to use your jetson stats

## Update the jetson-stats version

Now update your system monitor is easier then before.

```elm
sudo -H pip install -U jetson-stats
```

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
usage: jtop [-h] [-r REFRESH] [--debug] [--page PAGE] [--version]

jtop is a system monitoring utility and control. Runs on terminal

optional arguments:
  -h, --help   show this help message and exit
  -r REFRESH   refresh interval
  --debug      Run with debug logger
  --page PAGE  Open fix page
  --version    show program's version number and exit
```
### Controls
To control the your NVIDIA Jetson are available this keyboard commands:
* **a** Start/Stop jetson_clocks service (Note: jetson_clocks start only after 60s from up time)
* **e** Enable/Disable jetson_clocks on board boot
* **+** and **-** Increase and decrease the NVPmodel
* **p** and **m** Increase and decrease the Fan speed
### Pages
**jtop** have four different pages to control your NVIDIA Jetson:
1. **ALL** Are collected all information about your board: CPUs status, Memory, *GPU*, disk, fan and all status about jetson_clocks, NVPmodel and other
2. **GPU** A real time GPU history about your NVIDIA Jetson
3. **CTRL** You can control the status of you
4. **INFO** Are collected all information about libraries, CUDA, Serial Number, interfaces, ...
## [**jetson_release**][jetson_release]
The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetso_release.png)
## [**jetson_variables**][jetson_variables]
This script generate the easy environment variables to know which is your Hardware version of the Jetson and which Jetpack you have already installed

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_env.png)

[jtop]: https://github.com/rbonghi/jetson_stats/wiki/jtop
[jetson_variables]: https://github.com/rbonghi/jetson_stats/wiki/jetson_variables
[jetson_release]: https://github.com/rbonghi/jetson_stats/wiki/jetson_release
[jetson_performance]: https://github.com/rbonghi/jetson_stats/wiki/jetson_performance
[jetson_docker]: https://github.com/rbonghi/jetson_stats/wiki/jetson_docker
[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: http://www.nvidia.com/object/embedded-systems-dev-kits-modules.html
