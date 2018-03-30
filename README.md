# Jetson Easy setup configurator
**Welcome in the Jetson setup configurator**

Wisit the [Official website](http://rnext.it/project/jetson-easy/) or read the [Wiki](https://github.com/rbonghi/jetson_easy/wiki)

The idea of this project is automatically update and setup your [NVIDIA Jetson][NVIDIA Jetson] [TK1, TX1, TX2, TX2i] embedded board without wait a lot of time.

Main features:
* **Biddibi Boddibi Boo** is an automatic  NVIDIA Jetson installer, from update&upgrade, patch the kernel or install [ROS][ROS]
* The **Jetson_performance** is a service to control the performance of the board, **jetson_variables** add new environments variables and **jetson_release** show the information about the board.

## Biddibi Boddibi Boo

![Biddibi Boddibi Boo Logo](http://rnext.it/wp-content/uploads/2018/03/biddibi_boddibi_boo.png)

The main script is called `biddibi_boddibi_boo.sh` and you can setup in one shot all your board. The shell script execute:

1. **Update & Distribution upgrade & Upgrade** Update, upgrade and distribution upgrade the [NVIDIA Jetson][NVIDIA Jetson] in only one shot
2. **Install Jetson release and performance service** It's an automatic installer for **Jetson_performance**, **jetson_variables** and **jetson_release**
3. **Patch the NVIDIA Jetson from known errors** If your release of NVIDIA Jetson have errors or require a patch this module update and fix automatically
4. **Kernel Update** This module fix the NVIDIA Jetson and add the common drivers (FTDI, ACM, etc...)
5. **Set hostname** Update permantly the hostname of your board
6. **Install [ROS][ROS]** With this modules you install the release ROS in your board, add the workspace and set the ROS_MASTER_URI
7. **Set git user.name and user.email** in your NVIDIA Jetson
8. **Install standard packages** You can add in your NVIDIA Jetson the common packages (nano, htop, ... ) to ZED drivers (coming soon) and other...

## Jetson_performance, jetson_variables and jetson_release

* [**jetson_variables**](https://github.com/rbonghi/jetson_easy/wiki/jetson_variables) - This script generate the easy environment variables to know which is your Hardware version of the Jetson and which Jetpack you have already installed
* [**jetson_release**](https://github.com/rbonghi/jetson_easy/wiki/jetson_release) - The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]
* [**jetson_performance**](https://github.com/rbonghi/jetson_easy/wiki/jetson_performance) - This service load `jetson_clock.sh` has a linux service




[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: http://www.nvidia.com/object/embedded-systems-dev-kits-modules.html
[ROS]: http://www.ros.org/
