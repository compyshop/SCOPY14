# SCOPY15 to SCOPYQD: source changes

The diffs compare the maintained sources of SCOPY15 with those of SCOPYQD
(`diff -U2`). Each hunk is followed by a comment. Both versions assemble
byte-identical to the original `SCOPY15.COM` / `SCOPYQD.COM`
(`make` in this directory checks SCOPYQD).

Short summary: SCOPYQD.COM is a modified SCOPY15. The program code is
SCOPY15's; the changes are the version and credit text, a quad density
(80 tracks, double-sided, 1440 sectors of 256 bytes) in place of "DOUBLE", a
changed PERCOM block for it, and a different buffer for the high speed query.
The file layout is that of SCOPY14 (one segment `$2F00-$3FFF`) with the RUN
vector of SCOPY15. The file is 4364 bytes (SCOPY15: 3241).

## Loader and stub (`scopy15.m65` / `scopyqd.m65`)

The loader and stub code is unchanged. Only equates, the comments and the
file layout differ.

```diff
--- ../SCOPY14/scopy15.m65	2026-10-14 10:09:35.376252728 +0200
+++ scopyqd.m65	2026-10-14 11:22:47.753452421 +0200
@@ -1,13 +1,15 @@
-; SCOPY15.COM - "sectorcopy" for Atari 8-bit computers
+; SCOPYQD.COM - "sectorcopy" for Atari 8-bit computers
 ; Disassembled with radare2 (gen.py), reassembles with ATasm 1.06.
-; Original by Erwin Reuss, Compyshop 06/87; version 15 (C) 07/88 bibosoft
+; Original by Erwin Reuss, Compyshop 06/87; version QD (derived from SCOPY15)
 ; (c) ABBUC e.V. 2026 (https://abbuc.de)
 ; Licensed under GPLv2
 ;
 ; Build:
-;   atasm -r -oscopy15rom.bin scopy15rom.m65   ; resident part ($F400-$FFEA)
-;   atasm -oSCOPY15.NEW scopy15.m65            ; Atari DOS binary file
+;   atasm -r -oscopyqdrom.bin scopyqdrom.m65   ; resident part ($F400-$FFE9)
+;   atasm -oSCOPYQD.tmp scopyqd.m65            ; Atari DOS binary file
+;   python3 segorder.py SCOPYQD.tmp SCOPYQD.NEW ; RUNAD segment last
 ;
-; The file has four segments and a RUN vector:
+; The file has one segment $2F00-$3FFF (like SCOPY14, unlike SCOPY15) and a
+; RUN vector; the zero filled gaps are stored in the file:
 ;   $2F00  loader: copies the ROM character set ($E000-$E3FF) to $3000,
 ;          switches the OS ROM off and moves $3000-$3FFF to RAM at
@@ -16,6 +18,6 @@
 ;          and jumps into the resident program. At $013E it also holds
 ;          the exit to the OS (Shift+Control+Tab).
-;   $3400  resident program, assembled for $F400 (scopy15rom.m65). The
-;          font part $3000-$33FF is not in the file, the loader fills it.
+;   $3400  resident program, assembled for $F400 (scopyqdrom.m65). The
+;          font part $3000-$33FF is zero in the file, the loader fills it.
 ;   $3FFA  NMI / RESET / IRQ vectors
 ;   $02E0  RUNAD = $2F00
@@ -34,9 +36,9 @@
 RESBASE = $F0           ; page the resident part runs at
 IMAGE   = $30           ; page of the resident image (font part + file)
-TIMSTOP = $FE04         ; resident: stop the SIO timeout timer
+TIMSTOP = $FE03         ; resident: stop the SIO timeout timer
 OSENTRY = $E477         ; OS: entry used for the exit
 COLDST  = $F4ED         ; resident: cold start
-NMIADR  = $FE6A         ; resident: NMI handler
-IRQADR  = $FEA3         ; resident: IRQ handler
+NMIADR  = $FE69         ; resident: NMI handler
+IRQADR  = $FEA2         ; resident: IRQ handler
 RUNAD   = $02E0         ; OS: run address
 STUBRUN = $0100         ; STUB is executed here
@@ -145,11 +147,18 @@
 STUBEND                 ; (the loop also copies one byte past the end)

-; --- resident part, runs at $F400-$FFEA -------------------------------------
-        *= $3400
+; --- zero fill up to the resident part ($2FA4-$33FF; $3000-$33FF becomes ----
+; the font) -------------------------------------------------------------------
+        .REPT $3400-*
+        .BYTE $00
+        .ENDR
+
+; --- resident part, runs at $F400-$FFE9 -------------------------------------
 RESIDENT
-        .INCBIN "scopy15rom.bin"
+        .INCBIN "scopyqdrom.bin"
+        .REPT $3FFA-*
+        .BYTE $00
+        .ENDR

 ; --- vectors at $FFFA-$FFFF (the loader moves them with the rest) -----------
-        *= $3FFA
         .WORD NMIADR    ; NMI
         .WORD $0000     ; RESET (unused)
```

- **Resident addresses:** the credit text is 1 byte longer, so everything
  from `DASHES` on is +1 against SCOPY15. `FINDDRIVE` then shrinks by 2 bytes
  (see hunk 9), so everything after it is -1. `TIMSTOP`, `NMIADR` and
  `IRQADR` lie behind `FINDDRIVE` and move down by one, the only functional
  changes in this file.
- **Layout:** SCOPY15 stores four segments (`$2F00-$2FA3`, `$3400-$3FEA`,
  `$3FFA-$3FFF`, RUNAD). SCOPYQD stores `$2F00-$3FFF` as one segment: the gap
  `$2FA4-$33FF` (the area the loader overwrites with the ROM font) and the
  gap before the vectors are zero bytes in the file, which is the reason for
  the 1123 additional bytes. The RUNAD segment (`$02E0`) is still last
  (`segorder.py`).
- **Stub:** unchanged, including the exit to the OS at `$013E`.

## Resident program (`scopy15rom.m65` / `scopyqdrom.m65`)

```diff
--- ../SCOPY14/scopy15rom.m65	2026-10-14 10:08:57.650608954 +0200
+++ scopyqdrom.m65	2026-10-14 11:22:55.927420504 +0200
@@ -1,11 +1,11 @@
-; SCOPY15 - "sectorcopy" for Atari 8-bit, resident part
+; SCOPYQD - "sectorcopy" for Atari 8-bit, resident part
 ; Disassembled with radare2 (gen.py), reassembles with ATasm 1.06.
-; Original by Erwin Reuss, Compyshop 06/87; version 15 (C) 07/88 bibosoft
+; Original by Erwin Reuss, Compyshop 06/87; version QD (derived from SCOPY15, bibosoft / hwl)
 ; (c) ABBUC e.V. 2026 (https://abbuc.de)
 ; Licensed under GPLv2
 ;
 ; This code runs at $F400-$FFEA in the RAM under the OS ROM. It is stored
-; in SCOPY15.COM at $3400-$3FEA and moved up by the loader (scopy15.m65).
-; Build as raw binary:   atasm -r -oscopy15rom.bin scopy15rom.m65
+; in SCOPYQD.COM at $3400-$3FE9 and moved up by the loader (scopyqd.m65).
+; Build as raw binary:   atasm -r -oscopyqdrom.bin scopyqdrom.m65
 ;
 ;   $F000-$F3FF  character set (not part of the file, the loader copies the
@@ -88,5 +88,4 @@
 WPASS    = $7E          ; write pass counter, $FF before the first
 EMPTY    = $EF          ; <> 0: the sector has data (not all zero)
-HSIDX    = $00          ; FINDDRIVE: high speed index received here
 SLOWFLG  = $7F          ; $FF: this sector is being retried at normal speed
 RESTART  = $0100        ; RESET restart routine (loader stub)
@@ -98,5 +97,5 @@
 NORETRY  = $0319        ; $FF: no command retry any more
 SECBUF   = $0400        ; start of the sector buffer
-SECMAP   = $037D        ; 130 bytes: one bit per sector, 1 = has data
+SECMAP   = $037E        ; 130 bytes: one bit per sector, 1 = has data
 BANKWIN  = $4000        ; extended RAM bank window $4000-$7FFF

@@ -132,12 +131,14 @@
 TITLE                           ; 20 characters
         .SBYTE "   sectorcopy "
-        .SBYTE +$40,"1.5"
+        .SBYTE +$40,"2.0"
         .BYTE $00,$00,$00
-CREDIT                          ; "(C) 07/88 bibosoft"
-        .BYTE $80
-        .SBYTE +$C0,"(C)"
-        .BYTE $80
-        .SBYTE +$C0,"07/88"
-        .SBYTE +$80," bibosoft "
+CREDIT                          ; "bibosoft quad by hwl" (lower case: colour 3), the
+        .SBYTE +$80,"bibosoft"  ; separators are $A0 (the font's "@" in
+        .BYTE $A0               ; colour 2), no longer blanks
+        .SBYTE +$80,"quad"
+        .BYTE $A0
+        .SBYTE +$80,"by"
+        .BYTE $A0
+        .SBYTE +$80,"hwl"
 DASHES
         .REPT 20
@@ -541,5 +542,5 @@
         STA DENSITY
         BMI DENSMED
-        LDA #$05
+        LDA #$0A
         STA SECSTEP
         LDA DENSITY
@@ -558,5 +559,6 @@
 DENSDBL
         JSR PRINTI
-        .SBYTE "DOUBLE"
+        .SBYTE "QUAD"
+        .BYTE $00,$00
         NOP
 PREFORMAT
@@ -976,8 +978,8 @@
 CHKEND720
         LDA SECTOR
-        CMP #$D0
+        CMP #$A0
         BNE INCSECT
         LDA SECTOR+1
-        CMP #$02
+        CMP #$05
         BNE INCSECT
         SEC
@@ -1148,5 +1150,5 @@
         .BYTE 40,0,0,18,0,0,0,128,$FF,0,0,0
 PCDOUBLE
-        .BYTE 40,0,0,18,0,4,1,0,$FF,0,0,0
+        .BYTE 40,1,0,18,1,4,1,0,$FF,0,0,0
 PCMEDIUM
         .BYTE 40,0,0,26,0,4,0,128,$FF,0,0,0
@@ -1280,11 +1282,9 @@
         LDA #$3F        ; command $3F: get high speed index, 1 byte
         STA DCOMND
-        LDX #$00
-        STX DBUF        ; the answer goes to $0000 (HSIDX)
-        STX DBUF+1
-        INX
-        STX DBYT
+        LDA #$01
+        STA DBYT
         LDA #$40
         STA DSTATS
+        JSR BUFRESET    ; the answer goes to SECBUF
         JSR SIO
         BPL DRVFAST
@@ -1302,5 +1302,5 @@
         RTS
 DRVFAST
-        LDA HSIDX
+        LDA SECBUF
         LDY DUNIT
         STA DRVSPD,Y     ; high speed POKEY divisor for this drive
```

### Hunk by hunk

1. **Header:** names only. The resident part now ends at `$FFE9`.
2. **`HSIDX` removed, `SECMAP` = `$037E`:** `HSIDX` (`$00`) is no longer
   used (see 7). The sector bit map moves up one byte, from `$037D-$03FE` to
   `$037E-$03FF`; its 130 bytes now end at `$03FF`, directly below
   `SECBUF`. Every `SECMAP,X` reference follows through the label.
3. **Title:** the version shows "2.0" instead of "1.5".
4. **Credit line:** now "bibosoft quad by hwl" (20 characters, lower case =
   colour 3, as before). The words are separated by `$A0` instead of `$80`.
   `$A0` is character `$20` of the font ("@") in colour 2, so the separators
   show as "@" rather than blanks.
5. **Progress bar step:** for single and quad density `SECSTEP` is 10
   instead of 5. The disk has twice the sectors, so one bar step covers
   twice as many.
6. **Density name:** "DOUBLE" becomes "QUAD", padded with two zero
   (blank) screen codes so that the `PRINTI` text keeps its length and
   overwrites the old name completely.
7. **Last sector:** `CHKEND720` (used for single and double density) ends the
   disk at sector `$05A0` = 1440 instead of `$02D0` = 720. Single density
   disks go through the same test, so the program is a quad-density-only
   tool in practice (the medium density end, 1040, is unchanged).
8. **PERCOM block `PCDOUBLE`:** `40,0,0,18,0,4,1,0,...` becomes
   `40,1,0,18,1,4,1,0,...`. Byte 1 (step rate) is 1, byte 4 (sides - 1) is 1:
   40 tracks, 18 sectors, 2 sides, MFM, 256 bytes per sector, that is 1440
   sectors. `PCSINGLE` and `PCMEDIUM` are unchanged.
9. **`FINDDRIVE`:** the answer to command `$3F` (high speed index) was
   received at `$0000`; now `BUFRESET` points the buffer to `SECBUF`
   (`$0400`, main memory) and `DRVFAST` reads the divisor from there. The
   byte count is loaded with `LDA #$01` / `STA DBYT` (the old code did it
   via `INX`). `BUFRESET` also sets PORTB bit 4 (extended banks off), so the
   answer lands in main memory. Why the buffer was changed I cannot tell from
   the code.

Everything else is identical to SCOPY15; apart from the address shifts above,
a byte comparison of the two resident images shows no other difference.
