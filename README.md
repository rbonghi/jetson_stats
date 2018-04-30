# Jetson Easy setup configurator
**Welcome in the Jetson setup configurator** - Visit the [Official website](http://rnext.it/project/jetson-easy/) or read the [Wiki](https://github.com/rbonghi/jetson_easy/wiki)

The idea of this project is automatically update and setup your [NVIDIA Jetson][NVIDIA Jetson] [TK1, TX1, TX2, TX2i] embedded board without wait a lot of time.

Main features:
* [**Biddibi Boddibi Boo**](#biddibi-boddibi-boo) is an automatic and **REMOTE** NVIDIA Jetson installer, from update&upgrade, patch the kernel or install [ROS][ROS]
* The [**Jetson_performance**](#jetson_performance-jetson_variables-and-jetson_release) is a service to control the performance of the board, [**jetson_variables**](#jetson_performance-jetson_variables-and-jetson_release) add new environments variables and [**jetson_release**](#jetson_performance-jetson_variables-and-jetson_release) show the information about the board.

If you want start with this toolkit you can write in your server bash:
```console
ubuntu@server:~$ https://github.com/rbonghi/jetson_easy.git
ubuntu@server:~$ cd jetson_easy
ubuntu@server:~/jetson_easy$ ./biddibi_boddibi_boo.sh
```

## Biddibi Boddibi Boo

![Biddibi Boddibi Boo Logo](http://rnext.it/wp-content/uploads/2018/03/biddibi_boddibi_boo.png)

The main script is called `biddibi_boddibi_boo.sh` and you can setup in one shot all your board. The system has different modules to control your automatic installation, the list follow:
1. **Update & Distribution upgrade & Upgrade** Update, upgrade and distribution upgrade the [NVIDIA Jetson][NVIDIA Jetson] in only one shot
2. [**Install Jetson release and performance service**](#jetson_performance-jetson_variables-and-jetson_release) It's an automatic installer for [**Jetson_performance**][jetson_performance], [**jetson_variables**][jetson_variables] and [**jetson_release**][jetson_release]
3. **Patch the NVIDIA Jetson from known errors** If your release of NVIDIA Jetson have errors or require a patch this module update and fix automatically
4. **Kernel Update** This module fix the NVIDIA Jetson and add the common drivers (FTDI, ACM, etc...)
5. **Set hostname** Update permantly the hostname of your board
6. **Install [ROS][ROS]** With this modules you install the release ROS in your board, add the workspace and set the ROS_MASTER_URI
7. **Set git user.name and user.email** in your NVIDIA Jetson
8. **Install standard packages** You can add in your NVIDIA Jetson the common packages (nano, htop, ... ) to ZED drivers (coming soon) and other...

The `biddibi_boddibi_boo.sh` run with an [easy user interface](#interactive-user-interface) or you can use the [silent mode](#command-line) and following a setup file the system will be installed automatically without other messages. If you want know all features you can write:
```console
ubuntu@server:~/jetson_easy$ ./biddibi_boddibi_boo.sh -h
Bibbibi Boddibi Boo is an automatic install for different type of modules.
Usage:
./biddibi_boddibi_boo.sh [options]
options,
   -h|--help      | This help
   --nogui        | Launch the system in silent mode (Without GUI)
   -q|--quiet     | If required, force automatically the reboot
   -c [file]      | Load configuration file from other reference [file]
   -m [user@host] | Remote connection with NVIDIA Jetson host
   -p [passwd]    | Load password without any other request from the script
```
### Remote connection
The Bibbibi Boddibi Boo script recognize if the script run on the NVIDIA Jetson or remotely and request the address and the password to connect on your board.

![Biddibi Boddibi Boo - remote 3](http://rnext.it/wp-content/uploads/2018/04/remote3.jpg)

After savind the remote configuration the script automatically connect on your board without write again the user and the password.

![Biddibi Boddibi Boo - remote 1](http://rnext.it/wp-content/uploads/2018/04/remote1.jpg)

### Interactive user interface
When you launch the script you can read the information about your board, from user and hostname, release of the kernel to the NVIDIA Jetson hardware release if installed the version of [ROS][ROS]
![Biddibi Boddibi Boo - page 1](http://rnext.it/wp-content/uploads/2018/03/page1.jpg)

In second menu you can setup your board and setup which type of installation you like. Finally you can save and store all infromation in a file and use same setup for the future.
![Biddibi Boddibi Boo - page 2](http://rnext.it/wp-content/uploads/2018/03/page2.jpg)

Finally you can startup the installer and wait that **jetson_easy** complete the installation for you!

### Command line
Look like the Interactive user interface this command start the installer without show you any type of messages
```console
nvidia@tegra-ubuntu:~/jetson_easy$ ./biddibi_boddibi_boo.sh -q
```

## Jetson_performance, jetson_variables and jetson_release

* [**jetson_variables**][jetson_variables] - This script generate the easy environment variables to know which is your Hardware version of the Jetson and which Jetpack you have already installed
* [**jetson_release**][jetson_release] - The command show the status and all information about your [NVIDIA Jetson][NVIDIA Jetson]
* [**jetson_performance**][jetson_performance] - This service load `jetson_clock.sh` has a linux service



[jetson_variables]: https://github.com/rbonghi/jetson_easy/wiki/jetson_variables
[jetson_release]: https://github.com/rbonghi/jetson_easy/wiki/jetson_release
[jetson_performance]: https://github.com/rbonghi/jetson_easy/wiki/jetson_performance
[NVIDIA]: https://www.nvidia.com/
[NVIDIA Jetson]: http://www.nvidia.com/object/embedded-systems-dev-kits-modules.html
[ROS]: http://www.ros.org/
