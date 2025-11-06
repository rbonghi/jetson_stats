.. _thor_podgov_tuning:

===========================================
Thor 2GPU: Podgov Tuning & Visualization
===========================================

Jetson Thor introduces a new GPU performance governor — **``nvhost_podgov``** — which dynamically adjusts GPU frequency based on real-time utilization.
This jtop branch enhances Thor support by reading and visualizing its internal tuning parameters directly from sysfs.

-------------------------
Governor Parameters
-------------------------

The following fields are read from::

    /sys/class/devfreq/gpu-gpc-0/nvhost_podgov/

+---------------+--------------------------------------------+-----------+
| Parameter     | Description                                | Example   |
+===============+============================================+===========+
| ``k``         | Moving-average weight factor for load calc. | 3         |
+---------------+--------------------------------------------+-----------+
| ``load_target`` | Target GPU load percentage before freq up-scaling | 200 |
+---------------+--------------------------------------------+-----------+
| ``load_margin`` | Allowed deviation (margin) around target before adjustment | 100 |
+---------------+--------------------------------------------+-----------+

The governor computes its smoothed load using::

    load_avg = (load_avg * (2**k - 1) + load) / (2**k)

-------------------------
jtop GUI Integration
-------------------------

In the **2GPU** page, jtop now displays these parameters directly below the governor line::

    gov: nvhost_podgov
    k=3  load_target=200  load_margin=100

This enhancement allows immediate inspection of the GPU’s adaptive frequency behavior without leaving jtop.

-------------------------
Data Sources
-------------------------

+----------------+-----------------------------------------------------+--------------------------------------------+
| Metric         | Source                                              | Notes                                      |
+================+=====================================================+============================================+
| **GPU load**   | ``/sys/class/devfreq/gpu-gpc-0/{busy_time,total_time}`` or ``/nvhost_podgov/load`` | Auto-selected with power fallback |
+----------------+-----------------------------------------------------+--------------------------------------------+
| **VDD_GPU power** | ``INA3221`` via ``/sys/class/hwmon/hwmon*/in*_input`` and ``curr*_input`` | Used for utilization proxy when load not exported |
+----------------+-----------------------------------------------------+--------------------------------------------+
| **3D Scaling** | Maps to ``performance`` ↔ ``nvhost_podgov`` governor toggle | Clickable in GUI |
+----------------+-----------------------------------------------------+--------------------------------------------+
| **Rail-Gating** | Runtime PM control (``on`` ↔ ``auto``) | Clickable in GUI |
+----------------+-----------------------------------------------------+--------------------------------------------+

-------------------------
Technical Highlights
-------------------------

* **core/thor_power.py** → INA3221 / INA238 power monitor abstraction
* **core/thor_gpu.py** → GPU load, power-based utilization fallback, and podgov parameter export
* **gui/pgpu_thor.py** → Real-time curses UI rendering with second-line podgov metrics

-------------------------
Example Idle vs Load Calibration
-------------------------

+-------------+----------------+----------------+
| State       | Measured Power | Constant       |
+=============+================+================+
| Idle        | ≈ 5.5 W        | ``_GPU_IDLE_MW = 5525`` |
+-------------+----------------+----------------+
| Full Load   | ≈ 22 W         | ``_GPU_FULL_MW = 22050`` |
+-------------+----------------+----------------+

These constants allow jtop to estimate GPU utilization even when ``busy_time`` / ``total_time`` counters are unavailable.

-------------------------
Tip for Developers
-------------------------

If you wish to display these parameters dynamically elsewhere, reuse::

    from jtop.core.thor_power import read_podgov_params

    params = read_podgov_params()
    print(f"k={params['k']} load_target={params['load_target']} load_margin={params['load_margin']}")

This will produce a live readout directly from the ``/sys/class/devfreq/gpu-gpc-0/nvhost_podgov`` directory.

-------------------------
Summary
-------------------------

This addition completes the Thor 2GPU integration by unifying:
* Real GPU load and power data via INA3221 sensors,
* Dynamic frequency visualization through podgov parameters,
* Seamless interaction with 3D scaling and rail-gating in the jtop GUI.

