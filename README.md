<h1 align="center">

<b>jetson-stats</b>

[![jetson-stats](https://github.com/rbonghi/jetson_stats/raw/master/docs/images/jtop.png)](https://rnext.it/jetson_stats/)

</h1>

<p align="center">
  <a href="https://pypistats.org/packages/jetson-stats"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dw/jetson-stats.svg" /></a>
  <a href="https://badge.fury.io/py/jetson-stats"><img alt="PyPI version" src="https://badge.fury.io/py/jetson-stats.svg" /></a>
  <a href="https://www.python.org/"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/jetson-stats.svg" /></a>
  <a href="https://pypi.org/project/jetson-stats/"><img alt="PyPI - Format" src="https://img.shields.io/pypi/format/jetson-stats.svg" /></a>
  <a href="/LICENSE"><img alt="GitHub" src="https://img.shields.io/github/license/rbonghi/jetson_stats" /></a>
  <a href="https://snyk.io/advisor/python/jetson-stats"><img alt="jetson-stats" src="https://snyk.io/advisor/python/jetson-stats/badge.svg" /></a>
  <a href="https://hub.docker.com/r/rbonghi/jetson_stats"><img alt="Docker Image Size (tag)" src="https://img.shields.io/docker/image-size/rbonghi/jetson_stats/latest"></a>
  <a href="https://hub.docker.com/r/rbonghi/jetson_stats"><img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/rbonghi/jetson_stats" /></a>
  <a href="https://github.com/rbonghi/jetson_stats/actions?query=workflow%3A%22CI+%26+CD%22"><img alt="CI & CD" src="https://github.com/rbonghi/jetson_stats/workflows/CI%20&%20CD/badge.svg" /></a>
  <a href="https://github.com/rbonghi/jetson_stats/actions/workflows/github-code-scanning/codeql"><img alt="CodeQL" src="https://github.com/rbonghi/jetson_stats/actions/workflows/github-code-scanning/codeql/badge.svg?branch=master" /></a>
</p>
<p align="center">
  <a href="https://twitter.com/raffaello86"><img alt="Twitter Follow" src="https://img.shields.io/badge/Follow-%40raffaello86-1DA1F2?logo=twitter&style=social" /></a>
  <a href="https://www.instagram.com/robo.panther/"><img alt="robo.panther" src="https://img.shields.io/badge/Follow-robo.panther-E4405F?style=social&logo=instagram" /></a>
  <a href="https://discord.gg/BFbuJNhYzS"><img alt="Join our Discord" src="https://img.shields.io/discord/1060563771048861817?color=%237289da&label=discord" /></a>
</p>

**jetson-stats** is a package for **monitoring** and **control** your [NVIDIA Jetson](https://developer.nvidia.com/buy-jetson) [Orin, Xavier, Nano, TX] series.

jetson-stats is a powerful tool to analyze your board, you can use with a stand alone application with `jtop` or import in your python script, the main features are:

- Decode hardware, architecture, L4T and NVIDIA Jetpack
- Monitoring, CPU, GPU, Memory, Engines, fan
- Control NVP model, fan speed, jetson_clocks
- Importable in a python script
- Dockerizable in a container
- Do not need super user
- Tested on many different hardware configurations
- Works with all NVIDIA Jetpack

## Install

jetson-stats can be installed with [pip](https://pip.pypa.io), but need **superuser**:

```console
sudo pip3 install -U jetson-stats
```

_Don't forget to **logout/login** or **reboot** your board_

<div align="center">

**🚀 That's it! 🚀**

</div>

## Run

Start jtop it's pretty simple just write `jtop`!

```console
jtop
```

A simple interface will appear on your terminal, more capabilities are documented at [_jtop_](https://rnext.it/jetson_stats/jtop/jtop.html) page.

<div align="center">

[![jtop](https://github.com/rbonghi/jetson_stats/raw/master/docs/images/jtop.gif)](https://github.com/rbonghi/jetson_stats)

</div>

## Library

You can use jtop such a python library to integrate in your software

```python
from jtop import jtop

with jtop() as jetson:
    # jetson.ok() will provide the proper update frequency
    while jetson.ok():
        # Read tegra stats
        print(jetson.stats)
```

You can also use jtop with your _virualenv_!

More information available at [_advanced usage_](https://rnext.it/jetson_stats/advanced-usage.html) page.

## Docker

You can run directly in Docker jtop, you need only to:

1. Install jetson-stats on your **host**
2. Install jetson-stats on your container as well
3. Pass to your container `/run/jtop.sock:/run/jtop.sock`

You can try running this command

```console
docker run --rm -it -v /run/jtop.sock:/run/jtop.sock rbonghi/jetson_stats:latest
```

More information available at [_docker_](https://rnext.it/jetson_stats/docker.html) documentation page.

## Sponsorship

If your company benefits from this library, please consider [💖 sponsoring its development](https://github.com/sponsors/rbonghi).

## Documentation

jetson-stats has usage and reference documentation at <https://rnext.it/jetson_stats>, there is also a [🆘 troubleshooting](https://rnext.it/jetson_stats/troubleshooting.html) page.

## Community

jetson-stats has a [community Discord channel](https://discord.gg/BFbuJNhYzS) for asking questions and collaborating with other contributors. Drop by and say hello 👋
