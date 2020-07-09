#!/bin/bash
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2020 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


# Read CUDA version
if [ -f /usr/local/cuda/version.txt ]; then
    JETSON_CUDA=$(cat /usr/local/cuda/version.txt | sed 's/\CUDA Version //g')
else
    JETSON_CUDA="NOT_INSTALLED"
fi
# Jetson CUDA version
export JETSON_CUDA

# Read from OpenCV if is installed CUDA
opencv_read_cuda()
{
    # Red if use CUDA or not
    local OPENCV_VERSION_VERBOSE=$(opencv_version --verbose | grep "Use Cuda" )
    if [ ! -z "$OPENCV_VERSION_VERBOSE" ]; then
        # Read status of CUDA
        local OPENCV_CUDA_FLAG=$(echo $OPENCV_VERSION_VERBOSE | cut -f2 -d ':' | cut -f2 -d ' ' )
        if [ "$OPENCV_CUDA_FLAG" == "NO" ]; then
            # Set NO if cuda is not installed
            echo "NO"
        else
            # Set YES if cuda is installed
            echo "YES"
        fi
        return
    fi
    # read NVIDIA CUDA version
    OPENCV_VERSION_VERBOSE=$(opencv_version --verbose | grep "NVIDIA CUDA" )
    if [ ! -z "$OPENCV_VERSION_VERBOSE" ]; then
        # get information
        local OPENCV_CUDA_FLAG=$(echo $OPENCV_VERSION_VERBOSE | cut -f2 -d ':')
        OPENCV_CUDA_FLAG=${OPENCV_CUDA_FLAG//[[:blank:]]/}
        # Set YES if cuda is installed
        echo "YES"
        return
    fi
    echo "NO"
    return
}

if hash opencv_version 2>/dev/null; then
    JETSON_OPENCV="$(opencv_version)"
    # Read information about cuda status
    JETSON_OPENCV_CUDA=$(opencv_read_cuda)
else
    JETSON_OPENCV="NOT_INSTALLED"
    JETSON_OPENCV_CUDA="NO"
fi
# Opencv variables
export JETSON_OPENCV
export JETSON_OPENCV_CUDA

# Extract cuDNN version
JETSON_CUDNN=$(dpkg -l 2>/dev/null | grep -m1 "libcudnn")
if [ ! -z "$JETSON_CUDNN" ] ; then
    JETSON_CUDNN=$(echo $JETSON_CUDNN | sed 's/.*libcudnn[0-9] \([^ ]*\).*/\1/' | cut -d '-' -f1 )
else
    JETSON_CUDNN="NOT_INSTALLED"
fi
# Export NVIDIA CuDNN Library
export JETSON_CUDNN

# Extract TensorRT version
JETSON_TENSORRT=$(dpkg -l 2>/dev/null | grep -m1 " tensorrt ")
if [ ! -z "$JETSON_TENSORRT" ] ; then
    JETSON_TENSORRT=$(echo $JETSON_TENSORRT | sed 's/.*tensorrt \([^ ]*\).*/\1/' | cut -d '-' -f1 )
else
    JETSON_TENSORRT="NOT_INSTALLED"
fi
# Export NVIDIA CuDNN TensorRT
export JETSON_TENSORRT

# Extract Visionworks version
JETSON_VISIONWORKS=$(dpkg -l 2>/dev/null | grep -m1 "libvisionworks")
if [ ! -z "$JETSON_VISIONWORKS" ] ; then
    JETSON_VISIONWORKS=$(echo $JETSON_VISIONWORKS | sed 's/.*libvisionworks \([^ ]*\).*/\1/' )
else
    JETSON_VISIONWORKS="NOT_INSTALLED"
fi
# Export NVIDIA CuDNN VisionWorks
export JETSON_VISIONWORKS

# Extract VPI
JETSON_VPI=$(dpkg -l 2>/dev/null | grep -m1 "vpi")
if [ ! -z "$JETSON_VPI" ] ; then
    JETSON_VPI=$(echo $JETSON_VPI | sed 's/.*vpi \([^ ]*\).*/\1/' )
else
    JETSON_VPI="NOT_INSTALLED"
fi
# Export VPI
export JETSON_VPI

# Vulkan
JETSON_VULKAN_INFO=$(which vulkaninfo)
if [ ! -z $JETSON_VULKAN_INFO ] ; then
    JETSON_VULKAN_INFO=$($JETSON_VULKAN_INFO | grep -m1 "Vulkan Instance Version")
    JETSON_VULKAN_INFO=$(echo $JETSON_VULKAN_INFO | sed 's/.*: \([^ ]*\).*/\1/' )
else
    JETSON_VULKAN_INFO="NOT_INSTALLED"
fi
# Export VPI
export JETSON_VULKAN_INFO
#EOF
