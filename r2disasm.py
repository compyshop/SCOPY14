#!/usr/bin/env python3
"""Disassemble a 6502 region with radare2 and emit ATasm source.

usage: gen.py <bin> <base> <out.m65> <entry,...> [--data a-b,...] [--code a,...]
"""
import json, re, subprocess, sys

HW = {  # Atari hardware register names
 0xD000:'HPOSP0',0xD001:'HPOSP1',0xD002:'HPOSP2',0xD003:'HPOSP3',0xD004:'HPOSM0',
 0xD008:'SIZEP0',0xD00C:'SIZEM',0xD00D:'GRAFP0',0xD011:'GRAFM',0xD012:'COLPM0',
 0xD016:'COLPF0',0xD017:'COLPF1',0xD018:'COLPF2',0xD019:'COLPF3',0xD01A:'COLBK',
 0xD01B:'PRIOR',0xD01D:'GRACTL',0xD01E:'HITCLR',0xD01F:'CONSOL',0xD010:'TRIG0',0xD014:'PAL',
 0xD200:'AUDF1',0xD201:'AUDC1',0xD202:'AUDF2',0xD203:'AUDC2',0xD204:'AUDF3',0xD205:'AUDC3',
 0xD206:'AUDF4',0xD207:'AUDC4',0xD208:'AUDCTL',0xD209:'KBCODE',0xD20A:'SKRES',
 0xD20B:'POTGO',0xD20D:'SEROUT',0xD20E:'IRQEN',0xD20F:'SKCTL',
 0xD300:'PORTA',0xD301:'PORTB',0xD302:'PACTL',0xD303:'PBCTL',
 0xD400:'DMACTL',0xD401:'CHACTL',0xD402:'DLISTL',0xD403:'DLISTH',0xD404:'HSCROL',
 0xD405:'VSCROL',0xD407:'PMBASE',0xD409:'CHBASE',0xD40A:'WSYNC',0xD40B:'VCOUNT',
 0xD40E:'NMIEN',0xD40F:'NMIRES',
}
# read-side aliases at the same address are only used as labels when the
# instruction reads (keeps source readable; value is identical either way)
HW_R = {0xD20D:'SERIN',0xD20E:'IRQST',0xD20F:'SKSTAT',0xD209:'KBCODE',
        0xD40F:'NMIST',0xD20A:'RANDOM',0xD004:'P0PF'}

def parse_ranges(s):
    out = []
    for p in s.split(','):
        if p:
            a, b = p.split('-'); out.append((int(a, 16), int(b, 16)))
    return out

args = sys.argv[1:]
binf, base, outf, entries = args[0], int(args[1], 16), args[2], [int(x, 16) for x in args[3].split(',') if x]
data_ranges, extra_code, extern, inline_calls = [], [], {}, set()
i = 4
while i < len(args):
    if args[i] == '--data': data_ranges = parse_ranges(args[i+1])
    elif args[i] == '--inline': inline_calls = {int(x, 16) for x in args[i+1].split(',')}
    elif args[i] == '--code': extra_code = [int(x, 16) for x in args[i+1].split(',')]
    elif args[i] == '--sym':
        for p in args[i+1].split(','):
            n, v = p.split('='); extern[int(v, 16)] = n
    i += 2

blob = open(binf, 'rb').read()
end = base + len(blob)

# --- ask radare2 to decode an instruction at every address --------------------
cmds = ['e scr.color=0', 'e asm.cpu=6502'] + [f'pdj 1 @ {a:#x}' for a in range(base, end)]
script = '\n'.join(cmds) + '\n'
import tempfile, os
with tempfile.NamedTemporaryFile('w', suffix='.r2', delete=False) as tf:
    tf.write(script)
res = subprocess.run(['r2', '-q', '-a', '6502', '-m', hex(base), '-i', tf.name, binf],
                     capture_output=True, text=True)
os.unlink(tf.name)
lines = [l for l in res.stdout.splitlines() if l.startswith('[')]
assert len(lines) == len(blob), (len(lines), len(blob), res.stderr[:500])
ins = {}
for a, l in zip(range(base, end), lines):
    j = json.loads(l)[0]
    ins[a] = j

def in_data(a):
    return any(lo <= a <= hi for lo, hi in data_ranges)

def valid(a):
    j = ins.get(a)
    return j and j['type'] not in ('invalid', 'ill') and j['disasm'] not in ('invalid',) \
        and a + j['size'] <= end

def target(j):
    m = re.search(r'0x([0-9a-f]+)', j['disasm'])
    return int(m.group(1), 16) if m else None

# --- recursive descent ---------------------------------------------------------
code = {}          # addr -> size
inline_str = {}    # string start -> terminator ($EA) address
todo = list(entries) + extra_code
jsr_targets, jmp_targets = set(), set()
while todo:
    a = todo.pop()
    while base <= a < end and a not in code and not in_data(a):
        if not valid(a):
            print(f'warning: invalid opcode in code path at {a:04X}', file=sys.stderr)
            break
        j = ins[a]; code[a] = j['size']
        mn = j['disasm'].split()[0]
        t = target(j)
        if mn in ('jmp',) and '(' not in j['disasm']:
            todo.append(t); jmp_targets.add(t); break
        if mn == 'jmp':
            break
        if mn in ('rts', 'rti', 'brk'):
            break
        if mn == 'jsr':
            todo.append(t); jsr_targets.add(t)
            if t in inline_calls:      # inline $EA-terminated string follows
                s0 = a + 3; e0 = s0
                while blob[e0-base] != 0xEA: e0 += 1
                inline_str[s0] = e0
                todo.append(e0); break
        elif j['type'] == 'cjmp':
            todo.append(t); jmp_targets.add(t)
        a += j['size']

# --- labels --------------------------------------------------------------------
labels = {}
def lab(a):
    if a not in labels:
        labels[a] = (f'S{a:04X}' if a in jsr_targets else f'L{a:04X}')
    return labels[a]
for e in entries + extra_code:
    lab(e)
# map address -> start of containing code instruction
owner = {}
for a, s in code.items():
    for k in range(s): owner[a + k] = a

used_ext = {}
def fmt_addr(v, is_zp, reading):
    """Return symbolic text for an operand address."""
    if base <= v < end:
        if v in owner and owner[v] != v:       # points into an instruction
            o = owner[v]; return f'{lab(o)}+{v-o}'
        return lab(v)
    if v in extern:
        used_ext[extern[v]] = v; return extern[v]
    name = (HW_R.get(v) if reading else None) or HW.get(v)
    if name:
        used_ext[name] = v; return name
    return f'${v:02X}' if is_zp else f'${v:04X}'

READS = {'lda','ldx','ldy','cmp','cpx','cpy','bit','and','ora','eor','adc','sbc'}

def convert(a, j):
    d = j['disasm']
    mn, _, op = d.partition(' ')
    op = op.strip()
    size = j['size']
    if size == 1:
        if mn in ('asl', 'lsr', 'rol', 'ror'):
            return f'{mn.upper()} A'
        return mn.upper()
    if op.startswith('#'):
        v = int(op[1:], 16) if op[1:].startswith('0x') else int(op[1:])
        return f'{mn.upper()} #${v:02X}'
    m = re.search(r'0x([0-9a-f]+)', op)
    v = int(m.group(1), 16)
    if j['type'] == 'cjmp':
        return f'{mn.upper()} {fmt_addr(v, False, False)}'
    no_zp_form = mn in ('jmp', 'jsr') or (',y' in op and mn not in ('ldx', 'stx'))
    if size == 3 and v < 0x100 and not no_zp_form:
        return None   # absolute addressing of ZP address: ATasm would shrink it
    sym = fmt_addr(v, size == 2, mn in READS)
    o = op[:m.start()] + sym + op[m.end():]
    o = o.replace(',x', ',X').replace(',y', ',Y')
    return f'{mn.upper()} {o}'

# --- data labels from absolute operands (e.g. table bases) ---------------------
for a in sorted(code):
    j = ins[a]
    if j['size'] in (2, 3) and not j['disasm'].split()[1].startswith('#'):
        t = target(j)
        if t is not None and base <= t < end and (j['size'] == 3 or j['type'] == 'cjmp'):
            if t not in owner or owner[t] == t:
                lab(t)

# --- emit ----------------------------------------------------------------------
def scr_char(b):
    """Internal (screen) code -> printable ATASCII char, or None."""
    if b < 0x40: c = b + 0x20
    elif 0x60 <= b < 0x80: c = b
    else: return None
    ch = chr(c)
    if ch == '"' or not (ch.isalnum() or ch in ' .,:-!?()/%&*+=<>'):
        return None
    return ch

out = []
a = base
while a < end:
    if a in labels:
        out.append(f'{labels[a]}')
    if a in code:
        j = ins[a]
        txt = convert(a, j)
        raw = ' '.join(f'${blob[a-base+k]:02X}' for k in range(j['size']))
        if txt is None:
            out.append(f'        .BYTE {",".join(raw.split())} ; {j["disasm"]} (forced absolute)')
        else:
            out.append(f'        {txt}')
        a += j['size']
        continue
    # data run up to next label / code
    b = a + 1
    while b < end and b not in code and b not in labels:
        b += 1
    chunk = blob[a-base:b-base]
    # zero fill
    k = 0
    while k < len(chunk):
        z = k
        while z < len(chunk) and chunk[z] == chunk[k]:
            z += 1
        if z - k >= 16:
            out += [f'        .REPT {z-k}', f'        .BYTE ${chunk[k]:02X}', '        .ENDR']
            k = z; continue
        # screen-code text run
        inv = chunk[k] & 0x80
        t = k
        while t < len(chunk) and (chunk[t] & 0x80) == inv and scr_char(chunk[t] & 0x7F):
            t += 1
        if t - k >= 4:
            txt = ''.join(scr_char(c & 0x7F) for c in chunk[k:t])
            for p in range(0, len(txt), 32):   # ATasm overflows on long lines
                out.append('        .SBYTE ' + ('+$80,' if inv else '') + '"' + txt[p:p+32] + '"')
            k = t; continue
        n = k + 1
        while n < len(chunk) and n - k < 8:
            # stop before a text run or long fill
            tt = n
            while tt < len(chunk) and (chunk[tt] & 0x80) == (chunk[n] & 0x80) \
                    and scr_char(chunk[tt] & 0x7F): tt += 1
            zz = n
            while zz < len(chunk) and chunk[zz] == chunk[n]: zz += 1
            if tt - n >= 4 or zz - n >= 16: break
            n += 1
        out.append('        .BYTE ' + ','.join(f'${c:02X}' for c in chunk[k:n]))
        k = n
    a = b

hdr = [f'; disassembled from {binf} with radare2 (region ${base:04X}-${end-1:04X})', '']
for n, v in sorted(used_ext.items(), key=lambda x: x[1]):
    hdr.append(f'{n:<8}= ${v:04X}')
hdr += ['', f'        *= ${base:04X}', '']
open(outf, 'w').write('\n'.join(hdr + out) + '\n')
print(f'{len(code)} code instrs, {len(labels)} labels', file=sys.stderr)
