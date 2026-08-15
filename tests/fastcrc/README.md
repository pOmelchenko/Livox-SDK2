# Livox firmware-header CRC contract

Livox firmware headers use a seed-zero reflected CCITT checksum. The vendored
FastCRC method is named `mcrf4xx`, but the deployed profile is not standard
CRC-16/MCRF4XX because its initial value is `0x0000`, not `0xffff`.

The complete contract established from the public HAP and Mid-360 packages is:

- width: 16 bits;
- polynomial: `0x1021` (`0x8408` in the reflected implementation);
- initial value: `0x0000`;
- input and output reflection: enabled;
- final XOR: `0x0000`;
- checked span: header offsets 0 through 283 inclusive;
- stored checksum: offsets 284 and 285, little-endian;
- excluded data: the stored checksum itself and all firmware payload/tail bytes.

No profile variation was found between the current public HAP and Mid-360
packages. Standard MCRF4XX is retained in the regression as a separately named
negative control; changing the initial value would reject both packages.

SDK2 explicitly compiles `FastCRCsw.cpp`, whose legacy `mcrf4xx` entrypoint is
the seed-zero implementation exercised here. The separately vendored
`FastCRChw.cpp` is selected only by the upstream Arduino `KINETISK` build and
retains standard init `0xffff`; SDK2 does not compile that file. The official
headers store all multi-byte fields little-endian. Existing SDK2 parsing reads
those packed fields directly, so this evidence qualifies the current
little-endian SDK targets and does not make a new big-endian support claim.

## Public fixture provenance

The fixtures contain only the first 286 bytes of publicly downloadable official
Livox firmware packages. No firmware payload is retained in this repository.
They were downloaded and extracted on 2026-08-15.

| Family | Official package | Full-file SHA-256 | Official/recomputed MD5 | Header SHA-256 | Stored / standard CRC |
| --- | --- | --- | --- | --- | --- |
| Mid-360 | [`LIVOX_MID360_FW_v13.18.0244.bin`](https://terra-1-g.djicdn.com/65c028cd298f4669a7f0e40e50ba1131/Mid360/20250411/LIVOX_MID360_FW_v13.18.0244.bin) | `9f34f70861ae6bdbae55f637bbc8bac3571bd7404bbb840e4a7bd0fa544001de` | `146aaef9b5634c0ba4a2a34b08210140` | `daf5f00f3e0006c592270a303d7a3edcafdaefd014cf94dd3ab6fff5f2733fdf` | `0x402e` / `0x461b` |
| HAP | [`LIVOX_HAP_FW_15.05.01.21.bin`](https://terra-1-g.djicdn.com/65c028cd298f4669a7f0e40e50ba1131/HAP/LIVOX_HAP_FW_15.05.01.21.bin) | `64c35214ff759dad84811c1733c166a2c1fe9b944aa38d81c44675d32c8b4ac8` | `ad19fc5d923debf38ad1f51f7579ab4d` | `3d2652a42695943ef251d358617a5d1cdc8bfda9e841528c34a4885aead6791d` | `0xcd67` / `0xcb52` |

The Mid-360 and HAP product download pages identify these artifacts as their
respective official firmware releases. Their published MD5 values match the
downloaded files.

## Reproduction

For each package, verify the full-file digests, extract exactly 286 bytes, and
encode only that header as the tracked hexadecimal fixture:

```sh
shasum -a 256 LIVOX_...bin
md5 LIVOX_...bin
dd if=LIVOX_...bin of=header.bin bs=286 count=1
shasum -a 256 header.bin
xxd -p -c 32 header.bin > family-version-header.hex
```

Decode the fixture and evaluate bytes 0 through 283 with the reflected
`0x8408` update loop twice, once from `0x0000` and once from `0xffff`. Decode
bytes 284 and 285 as an unsigned little-endian value. The focused test performs
those comparisons on the exact same fixture bytes and keeps the textbook
`"123456789"` vectors separate from firmware compatibility evidence.

The seed-zero behavior and misleading standard-MCRF4XX comment were already
present in official Livox-SDK2 import commit
`30e53d5b93d80be0c0d699c9b16dc76996efc06c` (`livox
<cs@livoxtech.com>`, repository MIT license). This downstream change preserves
the deployed behavior and corrects its description.
