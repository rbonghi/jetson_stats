---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

## Describe the bug

A clear and concise description of what the bug is.

## To Reproduce

Steps to reproduce the behavior:

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Screenshots

If applicable, add screenshots to help explain your problem.

## Expected behavior

A clear and concise description of what you expected to happen.

## Additional context

Add any other context about the problem here.

### Board

Output from `jetson_release -v`:
<!-- Complete all fields

  You can find this data on:
   * jetson_release -v
   * jtop (page INFO)
-->

* jetson-stats version: [e.g. 1.8]
* P-Number: [e.g. pXXXX-XXXX]
* Module: [e.g. NVIDIA Jetson XXX]
* Jetpack: [e.g. 4.3]
* L4T: [e.g. 5.2.1]

### Log from jtop.service

Attach here the output from: `journalctl -u jtop.service -n 100 --no-pager`

<!-- Use:
journalctl -u jtop.service -n 100 --no-pager
 -->

### Log from jetson-stats installation

Attach here the output from: `sudo -H pip3 install --no-cache-dir -v -U jetson-stats`

<!-- Use:
sudo -H pip3 install --no-cache-dir -v -U jetson-stats
 -->

### RAW Data

File from `jtop --error-log` attached

<!-- Please attach the output from:
jtop --error-log
-->