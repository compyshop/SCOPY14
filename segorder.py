#!/usr/bin/env python3
"""Move the RUNAD segment ($02E0-$02E1) of an Atari DOS binary file to the
end. ATasm writes the segments sorted by address, SCOPY15.COM has the run
address last.

usage: segorder.py <in> <out>
"""
import sys

d = open(sys.argv[1], 'rb').read()
segs, i = [], 0
if d[:2] == b'\xff\xff':
    i = 2
while i < len(d):
    if d[i:i+2] == b'\xff\xff':      # optional header in front of a segment
        i += 2
    start = d[i] | d[i+1] << 8
    end = d[i+2] | d[i+3] << 8
    n = 4 + end - start + 1
    segs.append((start, d[i:i+n]))
    i += n
segs.sort(key=lambda s: s[0] == 0x02E0)      # stable: RUNAD goes last
with open(sys.argv[2], 'wb') as f:
    f.write(b'\xff\xff' + b''.join(s[1] for s in segs))
