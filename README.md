# Jetson Easy setup configurator
**Welcome in the Jetson setup configurator**

The idea of this project is automatically update and setup your [NVIDIA Jetson][NVIDIA Jetson] [TK1, TX1, TX2, iTX2] embedded board without wait a lot of time.

The main script is called `biddibi_boddibi_boo.sh` and you can setup in one shot all your board. The shell script execute:

* **Update & Distribution upgrade & Upgrade**
  
  Update, upgrade and distribution upgrade the [NVIDIA Jetson][NVIDIA Jetson] in only one shot

* **Install Jetson release and performance service**
  * [**jetson_variables**](https://github.com/rbonghi/jetson_easy/wiki/jetson_variables) - This script generate the easy environment variables to know which is your Hardware version of the Jetson and which Jetpack you have already installed
  * [**jetson_release**](https://github.com/rbonghi/jetson_easy/wiki/jetson_release) - The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]
  * [**jetson_performance**](https://github.com/rbonghi/jetson_easy/wiki/jetson_performance) - This service load `jetson_clock.sh` has a linux service
* Set hostname
* Install [ROS][ROS]
* **[COMING SOON]** Install USB and ACM driver

[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: http://www.nvidia.com/object/embedded-systems-dev-kits-modules.html
[ROS]: http://www.ros.org/
