# Jetson stats 
**Welcome in the Jetson setup configurator** - Visit the [Official website](http://rnext.it/project/jetson-easy/) or read the [Wiki](https://github.com/rbonghi/jetson_stat/wiki)

The idea of this project is automatically update and setup your [NVIDIA Jetson][NVIDIA Jetson] [Nano, Xavier, TX2i, TX2, TX1, TK1] embedded board without wait a lot of time.

## Install
To use all tools inside the jetson_stats you can run `install_jetson_stats.sh`, and follow the prompt. Other option are available following the help
```console
ubuntu@server:~/jetson_stats$ ./install_jetson_stats.sh -h
Jetson_stats, Installer for nvidia top and different information modules.
Usage:
./install_jetson_stats.sh [options]
options,
   -h|--help    | This help
   -s|--silent  | Run jetson_stats in silent mode
   -i|--inst    | Change default install folder
   -f|--force   | Force install all tools
   -auto        | Run at start-up jetson performance
   -uninstall   | Run the uninstaller
```

## [**jtop**][jtop] 
A Dynamic interface where is showed the status of your [NVIDIA Jetson][NVIDIA Jetson]. CPU, RAM, GPU status and frequency and other...

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jtop.png)

## [**jetson-docker**][jetson_docker]
It is a bridge to use the NVIDIA core inside your doker container. This bridge share CUDA library, and all devices (nvmap and gpu) 

## [**jetson_variables**][jetson_variables]
This script generate the easy environment variables to know which is your Hardware version of the Jetson and which Jetpack you have already installed

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetson_env.png)
## [**jetson_release**][jetson_release]
The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]

![jtop](https://github.com/rbonghi/jetson_stats/wiki/images/jetso_release.png)

## [**jetson_performance**][jetson_performance]
This service load `jetson_clock.sh` has a linux service

[jtop]: https://github.com/rbonghi/jetson_stats/wiki/jtop
[jetson_variables]: https://github.com/rbonghi/jetson_stats/wiki/jetson_variables
[jetson_release]: https://github.com/rbonghi/jetson_stats/wiki/jetson_release
[jetson_performance]: https://github.com/rbonghi/jetson_stats/wiki/jetson_performance
[jetson_docker]: https://github.com/rbonghi/jetson_stats/wiki/jetson_docker
[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: http://www.nvidia.com/object/embedded-systems-dev-kits-modules.html
