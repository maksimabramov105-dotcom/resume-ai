#!/usr/bin/env python3
"""
make_icons.py — Creates placeholder purple square PNG icons for the Chrome extension.
Uses only Python stdlib (struct + zlib). No Pillow required.

Usage:
    cd chrome_extension/icons
    python3 make_icons.py
"""
import os
import struct
import zlib


def create_png(width: int, height: int, r: int, g: int, b: int) -> bytes:
    """Generate a minimal valid PNG file with a solid RGB color."""

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR: width, height, bit depth=8, color type=2 (RGB), compression, filter, interlace
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b'IHDR', ihdr_data)

    # IDAT: raw pixel data, one scanline = filter byte (0) + RGB*width
    raw_row = bytes([0]) + bytes([r, g, b] * width)   # filter=None (0) + pixels
    raw_data = raw_row * height
    compressed = zlib.compress(raw_data, 9)
    idat = chunk(b'IDAT', compressed)

    # IEND
    iend = chunk(b'IEND', b'')

    return signature + ihdr + idat + iend


# Brand purple — matches --accent: #7c3aed
R, G, B = 124, 58, 237

script_dir = os.path.dirname(os.path.abspath(__file__))

for size in [16, 48, 128]:
    path = os.path.join(script_dir, f'icon{size}.png')
    png_bytes = create_png(size, size, R, G, B)
    with open(path, 'wb') as f:
        f.write(png_bytes)
    print(f'  Created {path}  ({size}x{size}, {len(png_bytes)} bytes)')

print()
print('Done. Replace with real icons before publishing to Chrome Web Store.')
print('Recommended: export from Figma or use a design tool with the brand gradient.')
