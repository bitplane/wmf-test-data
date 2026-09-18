# WMF test data

Test data for [pillow-wmf](https://github.com/bitplane/pillow-wmf).

Used as a test data to oracle mapping repo. WMFs are not mine, see individual
collections for source info, your mileage may vary, use at your own risk etc
etc.

`corpora/<name>/` holds the metafiles from one source.

## Reference images

One release per output size, the sizes being whatever `sizes.txt` lists:

    gh release download 257x193 -R bitplane/wmf-test-data

Assets are `<corpus>-<width>x<height>.tar.gz`, unpacking to
`<width>x<height>/<corpus>/` so several sizes share one cache directory without
colliding. A PNG sits at each metafile's path. Anything GDI would not draw has
no PNG.

## Making them

    gh workflow run references.yml

That renders every corpus and size combination the releases do not already have,
one Windows job per size, and nothing at all when they are all there. Add a line
to `sizes.txt` or a directory to `corpora/` and run it again to fill the gap.
Delete a release to have it rebuilt from scratch.
