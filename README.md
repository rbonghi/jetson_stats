# Jetson stats
[![PyPI - Downloads](https://img.shields.io/pypi/dw/jetson-stats.svg)](https://pypistats.org/packages/jetson-stats) [![PyPI version](https://badge.fury.io/py/jetson-stats.svg)](https://badge.fury.io/py/jetson-stats) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jetson-stats.svg)](https://www.python.org/) [![PyPI - Format](https://img.shields.io/pypi/format/jetson-stats.svg)](https://pypi.org/project/jetson-stats/) [![GitHub](https://img.shields.io/github/license/rbonghi/jetson_stats)](/LICENSE) [![Docker Pulls](https://img.shields.io/docker/pulls/rbonghi/jetson_stats)](https://hub.docker.com/r/rbonghi/jetson_stats) [![CI & CD](https://github.com/rbonghi/jetson_stats/workflows/CI%20&%20CD/badge.svg)](https://github.com/rbonghi/jetson_stats/actions?query=workflow%3A%22CI+%26+CD%22)

[![Twitter Follow](https://img.shields.io/twitter/follow/raffaello86?style=social)](https://twitter.com/raffaello86) [![robo.panther](https://img.shields.io/badge/Follow:-robo.panther-E4405F?style=social&logo=instagram)](https://www.instagram.com/robo.panther/) [![Discord](https://img.shields.io/discord/1060563771048861817)](https://discord.gg/BFbuJNhYzS)

**jetson-stats** is a package for **monitoring** and **control** your [NVIDIA Jetson][NVIDIA Jetson] [Orin, Xavier, Nano, TX1, TX2] series. Works with all NVIDIA Jetson ecosystem.

**Consider to** [:sparkling_heart: **Sponsor** jetson-stats](https://github.com/sponsors/rbonghi)

When you install jetson-stats are included:
- [Jetson stats](#jetson-stats)
- [Install](#install)
  - [Virtual environment](#virtual-environment)
  - [Docker](#docker)
  - [Troubleshooting](#troubleshooting)
- [jtop](#jtop)
  - [Pages](#pages)
  - [Controls](#controls)
- [jetson\_config](#jetson_config)
- [jetson\_release](#jetson_release)
- [jetson\_swap](#jetson_swap)
- [jetson variables](#jetson-variables)

Read the [Wiki](https://github.com/rbonghi/jetson_stat/wiki) for more detailed information or read the package [documentation](https://rnext.it/jetson_stats).

# Install

```console
sudo -H pip3 install -U jetson-stats
```
**🚀 That's it! 🚀** 

_PS: Don't forget to **reboot** your board_

**You can run jtop in your python script [read here][library]**

## Virtual environment

If you need to install in a virtual environment like *virtualenv*, you **must** install before in your host **and after** in your environment, like:
```
virtualenv venv
source venv/bin/activate
pip install -U jetson-stats
```

## Docker

You can run jtop from a docker container, but you **must** install jetsons-stats as well on your host! Try with the command below:
```console
docker run --rm -t -v /run/jtop.sock:/run/jtop.sock rbonghi/jetson-stats
```

or you can add in your Dockerfile writing:

```docker
FROM python:3-buster
RUN pip install -U jetson-stats
```

## Troubleshooting

If you reach the error below:

**sudo: pip: command not found**

You need to install **pip** before to install jetson-stats

```console
sudo apt-get install python3-pip
sudo -H pip3 install -U jetson-stats
```

**REMIND** to pass `/run/jtop.sock:/run/jtop.sock` when you run your docker container.

# [jtop][jtop] 
It is a system monitoring utility that runs on the terminal and see and **control** realtime the status of your [NVIDIA Jetson][NVIDIA Jetson]. CPU, RAM, GPU status and frequency and other...

The prompt interface will be show like this image, **now clickable!**:
![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jtop.gif)

You can run the jtop simple using a simple command `jtop`

YES! Sudo is **not** more required!
```console
nvidia@agx-orin:~/$ jtop
```

Other options are available with `-h` option:
```console
nvidia@agx-orin:~/$ jtop -h
usage: jtop [-h] [--no-warnings] [--restore] [--loop] [--color-filter] [-r REFRESH] [-p PAGE] [-v]

jtop is system monitoring utility and runs on terminal

optional arguments:
  -h, --help            show this help message and exit
  --no-warnings         Do not show warnings (default: False)
  --restore             Reset Jetson configuration (default: False)
  --loop                Automatically switch page every 5s (default: False)
  --color-filter        Change jtop base colors, you can use also JTOP_COLOR_FILTER=True (default: False)
  -r REFRESH, --refresh REFRESH
                        refresh interval (default: 500)
  -p PAGE, --page PAGE  Open fix page (default: 1)
  -v, --version         show program's version number and exit
```
You can change page using _left_, _right_ arrow or _TAB_ to change page.
## Pages
**jtop** have four different pages to control your NVIDIA Jetson:
1. **ALL** Are collected all information about your board: CPUs status, Memory, *GPU*, disk, fan and all status about jetson_clocks, NVPmodel and other
2. **GPU** A real time GPU history about your NVIDIA Jetson
3. **CPU** A real time CPU plot of NVIDIA Jetson
4. **MEM** A real time Memory chart and swap monitor
5. **CTRL** Enable/Disable **jetson_clocks**, **nvpmodel** or **fan** directly from here
6. **INFO** All information about libraries, CUDA, Serial Number, interfaces, ...
## Controls
To control the your NVIDIA Jetson are available this keyboard commands:

In page **4 MEM**:
* **c** Clear cache
* **s** Enable/Disable extra swap
* **+** and **-** Increase and decrease swap size

In page **5 CTRL**:
* **a** Start/Stop jetson_clocks service (Note: jetson_clocks start only after 60s from up time)
* **e** Enable/Disable jetson_clocks on board boot
* **+** and **-** Increase and decrease the NVPmodel
* **f** Manual/jetson_clocks mode for your fan
* **p** and **m** Increase and decrease the Fan speed

# [jetson_config][jetson_config]

Check _jetson-stats_ **health**, enable/disable **desktop**, enable/disable **jetson_clocks**, improve the performance of your **wifi** are available only in one click using **jetson_config**

![jetson_config](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_config.png)
# [jetson_release][jetson_release]
The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_release.png)
# [jetson_swap][jetson_swap]
Simple manager to switch on and switch off a swapfile in your jetson.

```console
nvidia@jetson-nano:~/$ sudo jetson_swap -h
usage: createSwapFile [[[-d directory ] [-s size] -a] | [-h] | [--off]]
  -d | --dir    <directoryname> Directory to place swapfile
  -n | --name   <swapname> Name swap file
  -s | --size   <gigabytes>
  -a | --auto   Enable swap on boot in /etc/fstab 
  -t | --status Check if the swap is currently active
  --off         Switch off the swap
  -h | --help   This message
```

# [jetson variables][jetson_variables]
When you install jetson-stats in your bash will be available a list of new environment variables to know which which hardware version is available are you working, which Jetpack is installed and other variable show below

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_env.png)

[library]: https://github.com/rbonghi/jetson_stats/wiki/library
[jtop]: https://github.com/rbonghi/jetson_stats/wiki/jtop
[jetson_config]: https://github.com/rbonghi/jetson_stats/wiki/jetson_config
[jetson_swap]: https://github.com/rbonghi/jetson_stats/wiki/jetson_swap
[jetson_variables]: https://github.com/rbonghi/jetson_stats/wiki/jetson_variables
[jetson_release]: https://github.com/rbonghi/jetson_stats/wiki/jetson_release
[jetson_performance]: https://github.com/rbonghi/jetson_stats/wiki/jetson_performance
[jetson_docker]: https://github.com/rbonghi/jetson_stats/wiki/jetson_docker
[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: https://developer.nvidia.com/buy-jetson
