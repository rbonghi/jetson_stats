# Mellanox NIC Temperature Fix Summary

## Problem Description

After installing MLNX_OFED v24.10-3.2.5.0 LTS on a Jetson platform with a Mellanox ConnectX-5 NIC:
- The NIC temperature was accessible via `sudo mget_temp -d 0005:01:00.0` and returned valid values (e.g., 44)
- However, the temperature reading disappeared from jtop's sensor-temp display
- This was inconsistent behavior - temperatures should be visible with or without MLNX_OFED

## Root Cause Analysis

The issue was in the `get_status()` method of the `TemperatureService` class in `jtop/core/temperature.py`:

1. **Storage Format**: Mellanox temperatures were correctly stored in millidegrees (e.g., 44000.0 for 44°C) in the `get_mellanox_temperature()` function
2. **Retrieval Issue**: When `get_status()` was called, it would pass through the millidegree value without conversion for Mellanox sensors
3. **Display Problem**: The GUI's `color_temperature()` function expected temperatures in Celsius, not millidegrees
4. **Missing Thresholds**: Mellanox sensors lacked default max/crit temperature values for proper color coding

## Changes Made

### 1. Fixed Temperature Conversion (jtop/core/temperature.py)

**File:** `jtop/core/temperature.py`
**Function:** `TemperatureService.get_status()`

**Before:**
```python
if isinstance(sensor.get('temp'), (int, float)):
    # Direct value from Mellanox
    values = {'temp': sensor['temp']}
```

**After:**
```python
if isinstance(sensor.get('temp'), (int, float)):
    # Direct value from Mellanox (stored in millidegrees)
    temp_value = sensor['temp'] / 1000.0
    values = {'temp': temp_value}
    # Add default max and crit values for Mellanox sensors
    values['max'] = 84  # Default max temperature
    values['crit'] = 100  # Default critical temperature
```

### 2. Improved Sudo Handling (jtop/core/temperature.py)

**File:** `jtop/core/temperature.py`
**Function:** `get_mellanox_temperature()`

**Before:**
```python
# Always used sudo
subprocess.run(['sudo', 'mget_temp', '-d', bus_addr], ...)
```

**After:**
```python
# Try without sudo first, then with sudo
temp_result = subprocess.run(['mget_temp', '-d', bus_addr], ...)
if temp_result.returncode != 0:
    # If failed without sudo, try with sudo
    temp_result = subprocess.run(['sudo', 'mget_temp', '-d', bus_addr], ...)
```

This improvement:
- Avoids sudo prompts when not needed
- Works better with the mlnx group permissions
- Provides better error handling

## Testing

### Test Results

All tests pass successfully:

1. **Temperature Conversion Test**: ✓
   - 44000.0 millidegrees correctly converted to 44.0°C
   - Default max (84°C) and crit (100°C) values set

2. **Temperature Service Test**: ✓
   - Multiple Mellanox sensors handled correctly
   - All temperatures properly converted

3. **Color Coding Test**: ✓
   - Temperatures below max: normal color
   - Temperatures between max and crit: yellow color
   - Temperatures above crit: red color

### Manual Verification

To verify the fix works on your system:

```bash
# Test the temperature reading
python3 -c "
import sys
sys.path.insert(0, '/path/to/jetson_stats')
from jtop.core.temperature import TemperatureService
service = TemperatureService()
service._temperature['test_mlx'] = {'temp': 44000.0}
status = service.get_status()
print(f'Temperature: {status[\"test_mlx\"][\"temp\"]}°C')
print(f'Max: {status[\"test_mlx\"][\"max\"]}°C')
print(f'Crit: {status[\"test_mlx\"][\"crit\"]}°C')
"
```

Expected output:
```
Temperature: 44.0°C
Max: 84°C
Crit: 100°C
```

## Backward Compatibility

The changes are fully backward compatible:

1. **Without MLNX_OFED**: Mellanox detection is skipped, traditional sensors work as before
2. **With MLNX_OFED**: Mellanox temperatures now display correctly
3. **Existing Sensors**: All other temperature sensors (hwmon, thermal) continue to work unchanged
4. **API**: No changes to the public API or data structures

## Deployment

To deploy this fix:

1. Update the code in `jtop/core/temperature.py`
2. Restart the jtop service:
   ```bash
   sudo systemctl restart jtop.service
   ```
3. Verify temperatures appear in jtop

## Troubleshooting

If temperatures still don't appear:

1. **Check MLNX_OFED installation**:
   ```bash
   which mget_temp
   ```

2. **Check Mellanox NIC detection**:
   ```bash
   lspci -d 15b3:
   ```

3. **Test manual temperature reading**:
   ```bash
   mget_temp -d <device_address>
   # or with sudo if needed
   sudo mget_temp -d <device_address>
   ```

4. **Check jtop logs**:
   ```bash
   journalctl -u jtop.service -f
   ```

5. **Add jtop user to mlnx group** (recommended):
   ```bash
   sudo usermod -a -G mlnx jtop
   sudo systemctl restart jtop.service
   ```

## Files Modified

- `jtop/core/temperature.py` - Fixed temperature conversion and sudo handling
- `MELLANOX_TEMP_README.md` - Updated documentation with troubleshooting and known issues

## Verification

The fix has been verified to:
- ✓ Correctly convert millidegrees to Celsius
- ✓ Add proper color coding thresholds
- ✓ Handle sudo permissions gracefully
- ✓ Maintain backward compatibility
- ✓ Pass all unit tests
