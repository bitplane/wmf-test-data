# malformed

Metafiles whose declared structure disagrees with their bytes, collected from
150 different discs rather than from one. Each subdirectory is a
[discmaster](https://discmaster.textfiles.com) item id, so `29478/` resolves at
`https://discmaster.textfiles.com/browse/29478`, and from there to the disc's
archive.org entry.

Sourcing them widely is the point. The other corpora hold 1,422 files with a
size mismatch but only 28 distinct deltas between the declared and actual
length, because a handful of tools each made the same mistake thousands of
times. These 468 files are wrong in 157 different ways, with trailing data
running to 10 KB where the rest of the repo tops out at 48 bytes.

Every file here is identifiable as a metafile: placeable magic, or a standard
header with a sane type and size. Files that merely carry a `.wmf` extension
while being JPEG or CorelDRAW were left out.
