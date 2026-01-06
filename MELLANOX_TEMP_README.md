# Mellanox NIC Temperature Support for jetson_stats

## Overview

This document describes the changes made to support Mellanox NIC temperature monitoring in jetson_stats when MLNX_OFED is installed.

## Problem

When MLNX_OFED is installed on a Jetson platform with a Mellanox ConnectX NIC:
- The NIC temperature is accessible via `mget_temp -d <device>`
- However, jtop was not detecting these temperatures
- The temperature readings disappeared from jtop after MLNX_OFED installation

## Solution

Modified the temperature monitoring system to detect and read Mellanox NIC temperatures using the MLNX_OFED `mget_temp` tool.

## Changes Made

### 1. Modified `jtop/core/temperature.py`

#### Added imports:
- `import subprocess` - for running `mget_temp` command

#### Added new function `get_mellanox_temperature()`:
- Detects if MLNX_OFED is installed by checking for `mget_temp`
- Uses `lspci` to find Mellanox devices (PCI vendor ID 15b3)
- Calls `sudo mget_temp -d <device>` for each Mellanox NIC
- Returns temperature data in the same format as other sensors

#### Modified `read_temperature()` function:
- Now handles both file paths (traditional sensors) and numeric values (Mellanox)
- Converts millidegrees to degrees Celsius for consistency

#### Modified `TemperatureService.__init__()`:
- Calls `get_mellanox_temperature()` to detect Mellanox NICs
- Merges Mellanox temperature data with existing sensors

#### Modified `TemperatureService.get_status()`:
- Handles both path-based and numeric temperature values
- Maintains compatibility with existing temperature sensors

### 2. Modified `jtop/service.py`

#### Updated `jtop_decode()` method:
- Simplified temperature data processing
- Relies on the updated temperature.py to handle all sensor types

## Usage

### With MLNX_OFED Installed

1. Install MLNX_OFED on your Jetson platform
2. Ensure `mget_temp` is in your PATH
3. Restart the jtop service:
   ```bash
   sudo systemctl restart jtop.service
   ```
4. Mellanox NIC temperatures will now appear in jtop with names like:
   - `mlx_0005_01_00_0` (based on PCI bus address)

### Without MLNX_OFED

The changes are backward compatible:
- If MLNX_OFED is not installed, Mellanox detection is skipped
- Traditional temperature sensors continue to work as before
- No changes to existing functionality

## Testing

Run the test script to verify Mellanox detection:
```bash
python3 test_mellanox_temp.py
```

## Technical Details

### Temperature Format

- Mellanox temperatures are stored in millidegrees (like other sensors)
- Example: 44°C is stored as 44000.0
- The `read_temperature()` function converts to Celsius for display

### Sensor Naming

Mellanox sensors are named using the PCI bus address:
- Format: `mlx_{bus}_{device}_{function}`
- Example: `mlx_0005_01_00_0` for device at 0005:01:00.0

### Error Handling

The implementation includes comprehensive error handling:
- Gracefully handles missing `mget_temp`
- Handles `lspci` failures
- Handles `mget_temp` timeouts
- Handles permission errors (uses sudo)
- Logs warnings for debugging

## Compatibility

- Works with all Mellanox ConnectX NICs
- Compatible with MLNX_OFED v24.10-3.2.5.0 and later
- Maintains backward compatibility with existing jtop installations
- No breaking changes to the API

## Troubleshooting

### Temperature not showing?

1. Check if MLNX_OFED is installed:
   ```bash
   which mget_temp
   ```

2. Check if Mellanox NICs are detected:
   ```bash
   lspci -d 15b3:
   ```

3. Test manual temperature reading:
   ```bash
   sudo mget_temp -d <device_address>
   ```

4. Check jtop logs for errors:
   ```bash
   journalctl -u jtop.service -f
   ```

### Permission issues?

The implementation now tries to run `mget_temp` without sudo first, and only falls back to sudo if needed.

To avoid sudo prompts, ensure the jtop user has permission to run `mget_temp`:

**Option 1: Add jtop user to mlnx group**
```bash
sudo usermod -a -G mlnx jtop
sudo systemctl restart jtop.service
```

**Option 2: Configure sudo to not require password**
```bash
# Edit sudoers file
sudo visudo

# Add this line (replace 'jtop' with the actual user if different)
jtop ALL=(ALL) NOPASSWD: /opt/mellanox/mft/bin/mget_temp
```

**Option 3: Run jtop with appropriate permissions**
```bash
# Run jtop as root (not recommended for production)
sudo jtop
```

## Known Issues and Fixes

### Issue: Temperature not displaying correctly after MLNX_OFED installation

**Problem:** After installing MLNX_OFED, Mellanox NIC temperatures would not display in jtop, even though `mget_temp` returned valid values.

**Root Cause:** The temperature values were being stored in millidegrees (e.g., 44000.0 for 44°C) but were not being converted to Celsius when retrieved via the `get_status()` method.

**Fix:** Updated the `get_status()` method in `jtop/core/temperature.py` to:
1. Convert millidegree values to Celsius for Mellanox sensors
2. Add default max (84°C) and crit (100°C) thresholds for proper color coding

**Status:** Fixed in current version

## Future Enhancements

Potential improvements for future versions:
- Support for multiple temperature sensors per NIC
- Reading max/crit thresholds from Mellanox (instead of using defaults)
- Automatic detection of MLNX_OFED version
- Support for other Mellanox tools (mstflint, etc.)
