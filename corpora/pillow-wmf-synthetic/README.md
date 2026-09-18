# pillow-wmf synthetics

Generated WMFs from [pillow-wmf](https://github.com/bitplane/pillow-wmf).
These are the broader compatibility cases outside its small local regression
suite: drawing, mapping, clipping, pens, brushes, palettes and bitmap transfers.

To export from a pillow-wmf checkout using its installed development environment:

```sh
python scripts/generate-wmf-fixtures.py --corpus /path/to/wmf-test-data/corpora/pillow-wmf-synthetic
```

Review additions, changes and obsolete inputs before tagging a release. The
normal release pipeline creates the Windows PNGs at the sizes in `sizes.txt`;
references do not belong in this directory or in Git history.
