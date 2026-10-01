# Offline Python cross-reference inventory

`python-3.14.7.inv` is the **unmodified** Sphinx inventory from the official
Python 3.14.7 HTML documentation archive. Bundling it keeps strict documentation
builds independent of the availability of `docs.python.org` while retaining
Python cross-reference links.

## Provenance

- Archive: https://www.python.org/ftp/python/doc/3.14.7/python-3.14.7-docs-html.tar.bz2
- Archive member: `python-3.14.7-docs-html/objects.inv`
- Archive SHA-256: `d484b784ec35c5776c5ff55f81fa984b5251a38b532b24bb00e43148bd73ffe9`
- Inventory SHA-256: `c6936c1ffd2369bd1bfe5083055962e9fa66ccee104debb21f499d3255b4fcdf`
- Inventory size: 158120 bytes; 19317 entries.
- The upstream inventory header identifies the documentation series as `3.14`.
- Python license: [`PSF-LICENSE.txt`](PSF-LICENSE.txt), copied verbatim from
  https://raw.githubusercontent.com/python/cpython/v3.14.7/LICENSE
- License SHA-256: `b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231`

`docs/conf.py` reads this local file and points generated links to
`https://docs.python.org/3.14`. There is deliberately no network inventory
fallback. Dependency installation still needs network access; the CI Sphinx
build runs in a network namespace without network access, with `-W` unchanged.

## Updating

1. Download the HTML documentation archive for the intended Python release from
   the official `www.python.org/ftp/python/doc/` directory.
2. Extract only its `objects.inv`; do not modify or synthesize inventory entries.
3. Update the filename and matching documentation-series URL in `docs/conf.py`,
   the upstream license, and the provenance/checksums above.
4. Run a fresh `sphinx-build -E -a -b html -W` with networking disabled. Verify
   that the generated Python cross-reference links are still present. A missing
   or corrupt inventory must continue to fail the build.
