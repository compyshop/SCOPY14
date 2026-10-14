# SCOPY14 – sectorcopy for Atari 8-bit computers

Original by Erwin Reuss, Compyshop 06/87
(c) ABBUC e.V. 2026 (https://abbuc.de)
Licensed under GPLv2

`SCOPY14.COM` is a disk sector copier for Atari 8-bit computers ("(P) 06/87
E.REUSS", German user interface). This directory contains a commented,
reassemblable source reconstructed from the binary, which builds back into
a byte-identical copy of the original.

## What the program does

SCOPY14 copies a whole floppy disk sector by sector, with one or two drives.

- **Densities:** single (720 × 128 bytes), medium/enhanced (1040 × 128) and
  double (720 × 256). The density of the original is detected with a STATUS
  command.
- **Drives:** it looks for the first drive (from D1:) as the source and the
  next one as the target. With only one drive it prompts for the original
  and target disk in turn.
- **High speed drives:** each drive is asked for its high speed index
  (command `$3F`), and transfers then run at that speed. On the first read
  error the source drops back to normal speed (19200 baud). High speed
  targets get a PERCOM block before formatting and a few drive-specific
  commands (`$20`, `$44`, `$51`).
- **Memory:** the program replaces the OS and uses almost all RAM as its
  buffer: main memory from `$0400`, `$C000-$CFFF`, `$D800-$EFFF` and every
  extended 130XE-style 16K bank. If the disk doesn't fit, it is copied in
  several passes.
- **Formatting:** the target can be formatted first in the source's
  density. Empty (all zero) sectors are then skipped when writing.
- **Errors:** a read or write error shows `DISK FEHLER #xx` with the SIO
  status. START retries, SELECT skips the sector (when reading), OPTION
  goes back to the menu.

### Menu (console keys)

| Key    | Function                                                        |
|--------|-----------------------------------------------------------------|
| START  | *Diskette kopieren*: copy the disk                              |
| SELECT | *Formatieren: JA/NEIN*: toggle formatting of the target         |
| OPTION | *Laufwerke austauschen*: swap source and target drive, or       |
|        | *Von Ramdisk schreiben*: write another copy when the whole disk |
|        | is still in memory                                              |

### How it works

The file is a single Atari DOS segment `$2F00-$3FFF` with no RUN or INIT
vector, so it is started at `$2F00`.

1. **Loader (`$2F00`):** copies the OS character set (`$E000-$E3FF`) to
   `$3000`, switches the OS ROM off and moves `$3000-$3FFF` into the RAM at
   `$F000-$FFFF`. It then copies a short routine to `$0100`, points the
   RESET vector (DOSINI) at it and runs it.
2. **Stub (`$0100`):** clears the hardware registers, sets the display and
   POKEY up and jumps to the resident program.
3. **Resident program (`$F000-$FFFF`):** the character set, display list,
   menu and copy logic. It has its own serial I/O routines (the OS is gone)
   and its own NMI/IRQ handlers.

## Files

| File             | Contents                                                   |
|------------------|------------------------------------------------------------|
| `SCOPY14.COM`    | the original binary                                        |
| `scopy14.m65`    | loader and stub; includes `scopy14rom.bin` at `$3000`      |
| `scopy14rom.m65` | resident program, assembled for `$F000`                    |
| `Makefile`       | builds both parts and compares the result with the original |
| `r2disasm.py`    | the radare2-based disassembler that made the first draft   |

The resident program has to run at `$F000` but is stored at `$3000`.
ATasm 1.06 has no directive for that, so it is assembled on its own as a
raw binary and pulled into the loader with `.INCBIN`.

## Building

Requirements: [ATasm](https://github.com/CycoPH/atasm) 1.06 and `make`.

```sh
make            # build SCOPY14.NEW and check it against SCOPY14.COM
make clean      # remove scopy14rom.bin and SCOPY14.NEW
```

By hand:

```sh
atasm -r -oscopy14rom.bin scopy14rom.m65   # resident part, raw $F000-$FFFF
atasm -oSCOPY14.NEW scopy14.m65            # Atari DOS binary file
cmp SCOPY14.COM SCOPY14.NEW
```

## Notes on the source

- The `.m65` files are the maintained source. They carry hand-made labels,
  variable names and comments. Running `r2disasm.py` again gives only a
  raw draft with generic labels (`LF4ED`, …).
- `PRINTI` prints the text that follows its `JSR`. The text ends with `$EA`,
  a `NOP` where execution then continues.
- Texts are in screen (internal) code (`.SBYTE`). In the GR.1/GR.2 lines,
  lower-case letters show as upper case in colour 3.
- ATasm 1.06 crashes ("stack smashing detected") on very long source lines,
  so long strings are split into pieces of at most 32 characters.
- ATasm doesn't warn when an equate and a label share a name. Run `make`
  after every change: the byte comparison catches mistakes like that.

### Reconstruction tool

`r2disasm.py` has radare2 decode every address (`pdj`), follows the code
from its entry points and writes ATasm source:

```sh
tail -c 4096 SCOPY14.COM > rom.bin           # the $3000-$3FFF part
python3 r2disasm.py rom.bin f000 rom.m65 f4ed,fdbb,fe32,fe6c \
        --data f000-f4ec,fffa-ffff --inline fc05
```

## SCOPY15

`SCOPY15.COM` ("(C) 07/88 bibosoft") is the newer version. Its source is
`scopy15.m65` (loader, stub, vectors, RUN address) and `scopy15rom.m65`
(resident program, now `$F400-$FFEA`). `make` builds it and compares it with
`SCOPY15.COM`; the result is byte-identical. ATasm writes the segments sorted
by address, so `segorder.py` moves the RUN address segment back to the end.

File layout: `$2F00-$2FA3` loader and stub, `$3400-$3FEA` resident program
(the font part `$3000-$33FF` is no longer in the file, the loader still fills
it from the ROM), `$3FFA-$3FFF` vectors, `$02E0` RUNAD = `$2F00`.
The file is 3241 bytes instead of 4358.

Changes against SCOPY14 (the full source diff with a comment for each
hunk is in [SCOPY15changes.md](SCOPY15changes.md)):

- **Sparse buffer:** all-zero sectors are no longer stored. During reading,
  the SIO receive routine ORs all bytes into `EMPTY` (`$EF`); `NEXTSECT`
  only advances the buffer pointer for sectors with data, and a bit map
  `SECMAP` (`$037D`, 130 bytes) remembers which sectors had data. So more
  of a disk fits into one pass. When writing, an empty sector is skipped on a
  formatted target; on an unformatted one (`Formatieren: NEIN`) the send
  routine sends zeros without reading the buffer.
- **High speed fallback per sector:** the source drive's divisor is restored
  before every sector and only the failing sector is retried at 19200 baud.
  An unreadable sector is kept as if it had data.
- **Formatting:** the PERCOM block is now sent to every target, not only to
  high speed drives. A format error is checked with the carry flag.
- **SIO:** the zero page variables moved from `$21-$2B` to `$E1-$EB` and the
  command frame from `$023A` to `$A0`. `PUTBYTE` also adds to the checksum,
  the timeout timer has no `WSYNC` delay and a receive timeout of 50 frames,
  format commands (`< $30`) get the long wait. `SIOSND` (`$41`) is the
  `AUDC4` value during SIO: `$A8` for the normal commands, 0 (silent) for the
  drive specific `$44`, `$4F` and `$51`; `$51` now gets aux `$FFFF`.
  `FINDDRIVE` takes the unit in X and receives the high speed index in `$00`.
- **Keys:** the console key debounce waits for 256 identical reads.
  Shift+Control+Tab (`KBCODE $EC`, checked in the NMI handler) leaves the
  program: the stub at `$013E` switches the OS ROM on and jumps to `$E477`.
- **Smaller things:** version "1.5" and the new credit line, the NMI handler
  no longer saves X and Y, the IRQ handler only switches the interrupts off,
  the "OPTION aborts" check after the target prompt, `SAVEDBARS` is 80 bytes.
