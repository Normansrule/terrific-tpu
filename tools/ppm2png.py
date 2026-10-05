#!/usr/bin/env python3
"""ppm2png.py - turn the VGA frames captured by tb/tb_vga.v (plain-text PPM, 4 bits
per colour) into PNG files.  usage: python3 tools/ppm2png.py in.ppm out.png"""
import sys
from PIL import Image
t = open(sys.argv[1]).read().split()
w, h, mx = int(t[1]), int(t[2]), int(t[3])
v = list(map(int, t[4:]))
img = Image.new("RGB", (w, h))
img.putdata([(v[i] * 255 // mx, v[i + 1] * 255 // mx, v[i + 2] * 255 // mx) for i in range(0, len(v), 3)])
img.save(sys.argv[2])
print("  wrote", sys.argv[2])
