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

# NVIDIA Identify version 
# reference: https://devtalk.nvidia.com/default/topic/1014424/jetson-tx2/identifying-tx1-and-tx2-at-runtime/
case $(cat /sys/module/tegra_fuse/parameters/tegra_chip_id) in
    64)
        JETSON_BOARD="TK1" ;;
    33)
        JETSON_BOARD="TX1" ;;
    24)
        JETSON_BOARD="TX2" ;;
    *)
        JETSON_BOARD="UNKNOWN" ;;
esac
JETSON_DESCRIPTION="NVIDIA Jetson $JETSON_BOARD"

# NVIDIA Jetson version
# reference https://devtalk.nvidia.com/default/topic/860092/jetson-tk1/how-do-i-know-what-version-of-l4t-my-jetson-tk1-is-running-/
JETSON_L4T_STRING=$(head -n 1 /etc/nv_tegra_release)

# Load release and revision
JETSON_L4T_RELEASE=$(echo $JETSON_L4T_STRING | cut -f 1 -d ',' | sed 's/\# R//g' | cut -d ' ' -f1)
JETSON_L4T_REVISION=$(echo $JETSON_L4T_STRING | cut -f 2 -d ',' | sed 's/\ REVISION: //g' | cut -d. -f1)

# Write Jetson description
JETSON_L4T="$JETSON_L4T_RELEASE.$JETSON_L4T_REVISION"

# Write version of jetpack installed
case $JETSON_L4T in
    "28.2") 
            JETSON_JETPACK="3.2" ;;
    "28.1") 
            JETSON_JETPACK="3.1" ;;
    *)
       JETSON_JETPACK="UNKNOWN" ;;
esac

