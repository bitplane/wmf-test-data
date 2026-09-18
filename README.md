# WMF test data

Test data for [pillow-wmf](https://github.com/bitplane/pillow-wmf).

Used as a test data to oracle mapping repo. WMFs are not mine, see individual
collections for source info, your mileage may vary, use at your own risk etc
etc.

`corpora/<name>/` holds the metafiles from one source. `sizes.txt` lists the
output sizes worth holding references for.

## Using a release

A release is one version of the corpus: the metafiles, and the Windows
references for every size, which means what you download from one release
agrees with itself.

    gh release download v1 -R bitplane/wmf-test-data -D cache
    for f in cache/*.tar.gz; do tar xzf "$f" -C cache; done

Unpacks to metafiles at `<corpus>/<path>.wmf` and references beside them at
`<size>/<corpus>/<path>.png`. A metafile with no PNG is one GDI would not draw.
Pull the assets you want with `-p 'borderart*'` rather than the whole set.

## Making one

Tag the commit, push the tag, then:

    gh workflow run references.yml

That publishes whatever the version's release does not already have, and
nothing at all when it is complete. Add a line to `sizes.txt` and run it again
to fill in that size. Change the metafiles and you want a new version, so tag
again.
