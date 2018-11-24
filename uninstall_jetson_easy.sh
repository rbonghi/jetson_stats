#!/bin/bash
# Copyright (C) 2018, Raffaello Bonghi <raffaello@rnext.it>
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright 
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its 
#    contributors may be used to endorse or promote products derived 
#    from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, 
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

JETSON_FOLDER="/etc/jetson_easy"
JETSON_BIN_FOLDER="/usr/local/bin"

# Uninstall the service
if service --status-all | grep -Fq 'jetson_performance'; then
    tput setaf 1
    echo "Stop and jetson_performance service"
    tput sgr0
    # Stop the service
    sudo service jetson_performance stop
fi

# Remove from bashrc jetsonstat variables
if grep -Fxq "#Jetson STAT variables" /home/$USER/.bashrc ; then
    echo "Remove Jetson STAT from bashrc"
    sed -i '/#Jetson STAT variables/d' /home/$USER/.bashrc
    sed -i '/source \/etc\/jetson_easy\/jetson_variables/d' /home/$USER/.bashrc
fi

# Remove configuration
if [ -f $JETSON_FOLDER/l4t_dfs.conf ]
then
    echo "Remove the jetson_clock.sh configuration"
    sudo rm $JETSON_FOLDER/l4t_dfs.conf
fi

# Remove symbolic link
if [ -f $JETSON_FOLDER/jetson_clocks.sh ]
then
    echo "Remove jetson_clock symbolic link"
    sudo rm $JETSON_FOLDER/jetson_clocks.sh
fi

# Remove the service
sudo update-rc.d -f jetson_performance remove

# Remove the service from /etc/init.d
if [ -f "/etc/init.d/jetson_performance" ]
then
    echo "Remove the service from /etc/init.d"
    sudo rm "/etc/init.d/jetson_performance"
fi

# Update service list
sudo systemctl daemon-reload

# Remove jetson_release link
if [ -f "$JETSON_BIN_FOLDER/jetson_release" ]
then
    echo "Remove jetson_release link"
    sudo rm "$JETSON_BIN_FOLDER/jetson_release"
fi

# Remove jetson_release link
if [ -f "$JETSON_BIN_FOLDER/jetson_swap" ]
then
    echo "Remove jetson_swap link"
    sudo rm "$JETSON_BIN_FOLDER/jetson_swap"
fi

# Remove jetson_easy folder
if [ -d "$JETSON_FOLDER" ]; then
    # remove folder
    echo "Remove jetson_easy folder"
    sudo rm -r $JETSON_FOLDER
fi

echo "Uninstall jetson_easy complete!"

