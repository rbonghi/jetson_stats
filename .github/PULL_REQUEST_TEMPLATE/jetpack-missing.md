# Add New Jetpack

To add a new NVIDIA Jetpack release you can quicky do:

Open file **`jtop/core/jetson_variables.py`** around line *49* there is a variable called **`NVIDIA_JETPACK`** add the new jetpack following the rule below:

```python
"L4T version": "Jetpack"
```

Checklist:

* [ ] Add Jetpack on **`jtop/core/jetson_variables.py`**
* [ ] Increase with a minor release jtop variable **`__version__`** in **`jtop/__init__.py`**
* [ ] See if all tests pass
* [ ] Merge the release pull request with message "`Jetpack Release <VERSION>`" where `<VERSION>` is the same release in **`jtop/__init__.py`**
* [ ] Get the release Pull request approved by a [CODEOWNER](https://github.com/rbonghi/jetson_stats/blob/master/.github/CODEOWNERS)
