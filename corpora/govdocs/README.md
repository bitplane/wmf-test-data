# govdocs

Metafiles extracted from the documents in
[govdocs1](https://digitalcorpora.org/corpora/file-corpora/files/).

Subdirectories are govdocs1 zip numbers. A file id's first three digits are its
zip, so `473/473051-00.wmf` is the first metafile embedded in govdocs1 file
`473051`.

Taken from the first 100 of the 1,000 zips. Zips 50 to 99 added no record type
that zips 0 to 49 had not already produced.

Extracted from Office Art BLIP records in OLE files, `\wmetafile` hex in RTF,
and media files in OOXML zips. Content is sniffed, not trusted to the extension.

Excluded: files over 20 KB, and files whose bytes are more than 60% `ESCAPE` or
blit records unless they carried a record nothing else had.
