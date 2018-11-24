#!/bin/bash

#NVIDIA Jetson TX1 TX2 TX2i
# Create a swap file and set up permissions
# If a parameter is passed, it should be the place to create the swapfile

SWAPDIRECTORY=$PWD
SWAPSIZE=8
AUTOMOUNT="N"

function usage
{
    echo "usage: createSwapFile [[[-d directory ] [-s size] -a] | [-h]]"
    echo "  -d | --dir   <directoryname>   Directory to place swapfile"
    echo "  -s | --size  <gigabytes>"
    echo "  -a | --auto  Enable swap on boot in /etc/fstab "
    echo "  -h | --help  This message"
}

while [ "$1" != "" ]; do
    case $1 in
        -d | --dir )            shift
                                SWAPDIRECTORY=$1
                                ;;
        -s | --size )           shift 
				SWAPSIZE=$1
                                ;;
        -a | --auto )           AUTOMOUNT="Y"
				;;
        -h | --help )           usage
                                exit
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done

if [[ $EUID != 0 ]]; then
    tput setaf 1
    echo "Launch with sudo!"
    tput sgr0
    
    usage
    
    exit 1
fi

echo "Creating Swapfile at: " $SWAPDIRECTORY
echo "Swapfile Size: " $SWAPSIZE"G"
echo "Automount: " $AUTOMOUNT

#Create a swapfile for Ubuntu at the current directory location
fallocate -l $SWAPSIZE"G" $SWAPDIRECTORY"/swapfile"
cd $SWAPDIRECTORY
#List out the file
ls -lh swapfile
# Change permissions so that only root can use it
sudo chmod 600 swapfile
#List out the file
ls -lh swapfile
#Set up the Linux swap area
sudo mkswap swapfile
#Now start using the swapfile
sudo swapon swapfile
#Show that it's now being used
swapon -s

if [ "$AUTOMOUNT" = "Y" ]; then
	echo "Modifying /etc/fstab to enable on boot"
        SWAPLOCATION=$SWAPDIRECTORY"/swapfile"
        echo $SWAPLOCATION
	sudo sh -c 'echo "'$SWAPLOCATION' none swap sw 0 0" >> /etc/fstab'
fi
