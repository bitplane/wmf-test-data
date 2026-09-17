# WMF test data

Test data for [pillow-wmf](https://github.com/bitplane/pillow-wmf).

Used as a test data to oracle mapping repo. WMFs are not mine, see individual
collections for source info, your mileage may vary, use at your own risk etc
etc.

`corpora/<name>/` holds the metafiles from one source.

## Reference images

One release per output size:

    gh release download 128x128 -R bitplane/wmf-test-data

Assets are `<corpus>-<width>x<height>.tar.gz`, holding the corpus tree with a PNG
beside each metafile's path. Anything GDI would not draw has no PNG.

To render a size that has no release yet:

    gh workflow run references.yml -f size=256
    gh workflow run references.yml -f size=256x192 -f corpus=wmffuzz
