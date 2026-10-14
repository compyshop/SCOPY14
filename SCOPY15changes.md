# SCOPY14 to SCOPY15: source changes

The diffs compare the maintained sources of SCOPY14 with those of SCOPY15
(`diff -U2`). Each hunk is followed by a comment. Both versions assemble
byte-identical to the original `SCOPY14.COM` / `SCOPY15.COM`.

Short summary: SCOPY15 does not store sectors that are all zero (sector bit
map `SECMAP`), retries high speed per sector, always sends the density block
before formatting, has a reworked serial routine and NMI handler, a stricter
key debounce, an exit to the OS (Shift+Control+Tab) and a new credit line.
The file is 3241 bytes instead of 4358, because the font area and padding
are no longer stored.

## Loader and stub (`scopy14.m65` / `scopy15.m65`)

### 1. -1,19 +1,23

```diff
-; SCOPY14.COM - "sectorcopy" for Atari 8-bit computers
+; SCOPY15.COM - "sectorcopy" for Atari 8-bit computers
 ; Disassembled with radare2 (gen.py), reassembles with ATasm 1.06.
-; Original by Erwin Reuss, Compyshop 06/87
+; Original by Erwin Reuss, Compyshop 06/87; version 15 (C) 07/88 bibosoft
 ; (c) ABBUC e.V. 2026 (https://abbuc.de)
 ; Licensed under GPLv2
 ;
 ; Build:
-;   atasm -r -oscopy14rom.bin scopy14rom.m65   ; resident part ($F000-$FFFF)
-;   atasm -oSCOPY14.NEW scopy14.m65            ; Atari DOS binary file
+;   atasm -r -oscopy15rom.bin scopy15rom.m65   ; resident part ($F400-$FFEA)
+;   atasm -oSCOPY15.NEW scopy15.m65            ; Atari DOS binary file
 ;
-; The file is a single segment $2F00-$3FFF without RUN/INIT vector:
+; The file has four segments and a RUN vector:
 ;   $2F00  loader: copies the ROM character set ($E000-$E3FF) to $3000,
 ;          switches the OS ROM off and moves $3000-$3FFF to RAM at
 ;          $F000-$FFFF, then copies STUB to $0100 and runs it there.
-;   $2F60  STUB (runs at $0100): clears hardware, sets up ANTIC/POKEY
-;          and jumps into the resident program.
-;   $3000  resident program, assembled for $F000 (scopy14rom.m65).
+;   $2F5E  STUB (runs at $0100): clears hardware, sets up ANTIC/POKEY
+;          and jumps into the resident program. At $013E it also holds
+;          the exit to the OS (Shift+Control+Tab).
+;   $3400  resident program, assembled for $F400 (scopy15rom.m65). The
+;          font part $3000-$33FF is not in the file, the loader fills it.
+;   $3FFA  NMI / RESET / IRQ vectors
+;   $02E0  RUNAD = $2F00

 HPOSP0  = $D000
```

**Comment:** Header only: file name, credit and the new memory
map. The file now has four segments and a RUN address instead of one
segment without one.

### 2. -21,14 +25,19

```diff
 SKCTL   = $D20F
 PORTB   = $D301
+PBCTL   = $D303
 DMACTL  = $D400
 CHACTL  = $D401
 CHBASE  = $D409
 NMIEN   = $D40E
-NMIRES  = $D40F

 ROMCHR  = $E0           ; page of the OS character set
 RESBASE = $F0           ; page the resident part runs at
-TIMSTOP = $FDBB         ; resident: stop the SIO timeout timer
+IMAGE   = $30           ; page of the resident image (font part + file)
+TIMSTOP = $FE04         ; resident: stop the SIO timeout timer
+OSENTRY = $E477         ; OS: entry used for the exit
 COLDST  = $F4ED         ; resident: cold start
+NMIADR  = $FE6A         ; resident: NMI handler
+IRQADR  = $FEA3         ; resident: IRQ handler
+RUNAD   = $02E0         ; OS: run address
 STUBRUN = $0100         ; STUB is executed here
```

**Comment:** New equate `PBCTL` (`$D303`) for the stub; `NMIRES` is no
longer used there. `TIMSTOP` moved from `$FDBB` to `$FE04`. `IMAGE` is
the page of the resident image in memory (`$3000`): until now
`>RESIDENT` was used for it, but `RESIDENT` is now `$3400` (the font
part is no longer in the file). `NMIADR`, `IRQADR` and `OSENTRY` are
needed for the vector segment and the new OS exit, `RUNAD` for the run
address.

### 3. -55,5 +64,5

```diff
         LDA #ROMCHR
         STA SRC+1
-        LDA #>RESIDENT
+        LDA #IMAGE
         STA DST+1
 CHRLP
```

**Comment:** The font copy loop still writes the ROM character set to
`$3000-$33FF`, so the destination page is now `IMAGE` (`$30`), not the
page of `RESIDENT`.

### 4. -72,8 +81,7

```diff
         ORA #$02        ; bit 1 = 1: BASIC off
         STA PORTB
-        LDY #$00
-        LDA #RESBASE
+        LDA #RESBASE    ; (Y is still 0)
         STA SRC+1       ; now used as destination: $F000
-        LDA #>RESIDENT
+        LDA #IMAGE
         STA DST+1       ; now used as source: $3000
 MOVLP
```

**Comment:** The `LDY #$00` is gone: Y is already 0 when the font copy
loop ends (INY/BNE). The image source page is again `IMAGE`.

### 5. -104,5 +112,4

```diff
 STUB
         SEI
-        STA NMIRES
         LDA #$00
         TAY
```

**Comment:** The stub no longer writes NMIRES (`$D40F`) right after SEI.

### 6. -117,10 +124,12

```diff
         ORA #$FC
         STA PORTB
-        LDA #$22
-        STA DMACTL
+        LDA #$3C        ; PBCTL $3C: SIO command line high
+        STA PBCTL
         LDA #RESBASE    ; font at $F000
         STA CHBASE
         LDA #$02
         STA CHACTL
+        LDA #$22
+        STA DMACTL
         LDA #$03
         STA SKCTL
```

**Comment:** New: the stub sets `PBCTL` to `$3C` (SIO command line
high, the idle state). The order of the ANTIC register writes changed
(CHBASE, CHACTL, then DMACTL), the values are the same.

### 7. -129,11 +138,23

```diff
         JSR TIMSTOP
         JMP COLDST
-STUBEND                 ; (the loop also copies this one byte)
-
-        .REPT 100
-        .BYTE $00
-        .ENDR
+; Exit to the OS, entered at $013E from the NMI handler (Shift+Control+Tab):
+; OS ROM back on, then jump into the OS (the RAM under it is left as is).
+        LDA #$FF
+        STA PORTB
+        JMP OSENTRY
+STUBEND                 ; (the loop also copies one byte past the end)

-; --- resident part, runs at $F000-$FFFF -------------------------------------
+; --- resident part, runs at $F400-$FFEA -------------------------------------
+        *= $3400
 RESIDENT
-        .INCBIN "scopy14rom.bin"
+        .INCBIN "scopy15rom.bin"
+
+; --- vectors at $FFFA-$FFFF (the loader moves them with the rest) -----------
+        *= $3FFA
+        .WORD NMIADR    ; NMI
+        .WORD $0000     ; RESET (unused)
+        .WORD IRQADR    ; IRQ
+
+; --- run address ------------------------------------------------------------
+        *= RUNAD
+        .WORD START
```

**Comment:** The stub gets a second entry at `$013E` (stub start
`$0100` + `$3E`): it switches the OS ROM back on and jumps to
`$E477`. The NMI handler uses it for Shift+Control+Tab. The 100 pad
bytes are gone and the stub is 70 bytes (the copy loop still copies
one byte past it). The resident part is now placed at `$3400` and
holds only `$F400-$FFEA`; the vectors `$3FFA-$3FFF` and the run
address `$02E0` (`START`) are written as extra segments.

## Resident program (`scopy14rom.m65` / `scopy15rom.m65`)

### 1. -1,19 +1,20

```diff
-; SCOPY14 - "sectorcopy" for Atari 8-bit, resident part
+; SCOPY15 - "sectorcopy" for Atari 8-bit, resident part
 ; Disassembled with radare2 (gen.py), reassembles with ATasm 1.06.
-; Original by Erwin Reuss, Compyshop 06/87
+; Original by Erwin Reuss, Compyshop 06/87; version 15 (C) 07/88 bibosoft
 ; (c) ABBUC e.V. 2026 (https://abbuc.de)
 ; Licensed under GPLv2
 ;
-; This code runs at $F000-$FFFF in the RAM under the OS ROM. It is stored
-; in SCOPY14.COM at $3000-$3FFF and moved up by the loader (scopy14.m65).
-; Build as raw binary:   atasm -r -oscopy14rom.bin scopy14rom.m65
+; This code runs at $F400-$FFEA in the RAM under the OS ROM. It is stored
+; in SCOPY15.COM at $3400-$3FEA and moved up by the loader (scopy15.m65).
+; Build as raw binary:   atasm -r -oscopy15rom.bin scopy15rom.m65
 ;
-;   $F000-$F3FF  character set (zero here, the loader copies the ROM font in)
+;   $F000-$F3FF  character set (not part of the file, the loader copies the
+;                ROM font in)
 ;   $F400        display list (DLIST), screen texts
 ;   $F4ED        cold start (entered from the loader stub)
-;   $FC05        print inline string: JSR, then text at $FE7C+Y,
+;   $FC41        print inline string: JSR, then text at SCREEN+Y,
 ;                terminated by $EA (a NOP that execution continues at)
-;   $FE7C        screen line buffer
-;   $FFFA        NMI / RESET / IRQ vectors
+;   $FEAB        screen line buffer
+;   $FFFA        NMI / RESET / IRQ vectors (written by the loader file)

 COLPF0  = $D016
```

**Comment:** Header only: the resident part now starts at `$F400`,
ends at `$FFEA`, the inline print routine moved to `$FC41` and the
screen buffer to `$FEAB`.

### 2. -25,4 +26,5

```diff
 AUDC4   = $D207
 AUDCTL  = $D208
+KBCODE  = $D209
 SKRES   = $D20A
 SEROUT  = $D20D
```

**Comment:** New hardware register name `KBCODE` for the keyboard
check in the NMI handler.

### 3. -42,12 +44,11

```diff

 ; --- variables -------------------------------------------------------------
-POKMSK   = $10          ; OS: POKEY IRQ mask (restored after SIO)
 DRVSPD   = $1B          ; POKEY divisor per drive, DRVSPD+unit (1-4)
-DUNIT    = $21          ; SIO: drive number
-DCOMND   = $22          ; SIO: command
-DSTATS   = $23          ; SIO: direction ($40 in, $80 out) / status
-DBUF     = $24          ; SIO: buffer address (2 bytes)
-DBYT     = $28          ; SIO: byte count (2 bytes)
-DAUX     = $2A          ; SIO: aux1/aux2 = sector number (2 bytes)
+DUNIT    = $E1          ; SIO: drive number
+DCOMND   = $E2          ; SIO: command
+DSTATS   = $E3          ; SIO: direction ($40 in, $80 out) / status
+DBUF     = $E4          ; SIO: buffer address (2 bytes)
+DBYT     = $E8          ; SIO: byte count (2 bytes)
+DAUX     = $EA          ; SIO: aux1/aux2 = sector number (2 bytes)
 SIOSTAT  = $30          ; SIO: result status
 CHKSUM   = $31          ; SIO: frame checksum
```

**Comment:** `POKMSK` is not used any more (SIO no longer restores
IRQEN from the OS mask). The SIO parameter block moved from zero page
`$21-$2B` to `$E1-$EB`; all code uses the names, so only the equates
change.

### 4. -65,5 +66,5

```diff
 TGTFMTD  = $3F          ; <> 0: target already formatted
 PRPTR    = $43          ; PRINTI: text pointer (2 bytes)
-ATRACT   = $4D          ; OS: attract mode counter
+SIOSND   = $41          ; AUDC4 value during SIO ($A8 audible, 0 silent)
 SECTOR   = $60          ; current sector (2 bytes)
 NEXTSEC  = $62          ; first sector of the next pass (2 bytes)
```

**Comment:** `ATRACT` (attract mode counter) is not touched any
more. New `SIOSND` (`$41`): the AUDC4 value used while SIO runs. It is
`$A8` (audible) for normal commands and 0 (silent) for the drive
specific commands `$44`, `$4F` and `$51`.

### 5. -72,5 +73,5

```diff
 CURBANK  = $67          ; current extended bank
 NUMBANKS = $68          ; number of extended 16K banks
-SAVSPD   = $69          ; source high speed divisor during fallback
+SAVSPD   = $69          ; source high speed divisor (read phase)
 RAMTOP   = $6A          ; end of main RAM (high byte: $80/$A0/$C0)
 SRCDRV   = $70          ; source drive
```

**Comment:** Comment only: `SAVSPD` now holds the source divisor
during the whole read phase.

### 6. -86,19 +87,19

```diff
 DENSITY  = $7D          ; $00 single, $20 double, $80 medium
 WPASS    = $7E          ; write pass counter, $FF before the first
-SLOWFLG  = $7F          ; $FF: source fell back to normal speed
+EMPTY    = $EF          ; <> 0: the sector has data (not all zero)
+HSIDX    = $00          ; FINDDRIVE: high speed index received here
+SLOWFLG  = $7F          ; $FF: this sector is being retried at normal speed
 RESTART  = $0100        ; RESET restart routine (loader stub)
+OSEXIT   = $013E        ; loader stub: OS ROM on, jump to $E477
 TIMER    = $0218        ; SIO timeout counter in frames (2 bytes)
 TIMVEC   = $0226        ; timer expiry vector (2 bytes)
-CMDFRM   = $023A        ; SIO command frame: device, command, aux1, aux2
+CMDFRM   = $00A0        ; SIO command frame: device, command, aux1, aux2
 SIOSTK   = $0318        ; stack pointer for the SIO error exit
 NORETRY  = $0319        ; $FF: no command retry any more
 SECBUF   = $0400        ; start of the sector buffer
+SECMAP   = $037D        ; 130 bytes: one bit per sector, 1 = has data
 BANKWIN  = $4000        ; extended RAM bank window $4000-$7FFF

-        *= $F000
-
-        .REPT 1024
-        .BYTE $00
-        .ENDR
+        *= $F400
 ; --- display list -----------------------------------------------------------
 DLIST
```

**Comment:** New variables: `EMPTY` (`$EF`, <> 0: the sector has
data), `HSIDX` (`$00`, where FINDDRIVE receives the high speed index),
`OSEXIT` (`$013E`), `SECMAP` (`$037D`, sector bit map). The SIO
command frame `CMDFRM` moved from `$023A` to zero page
`$A0`. `SLOWFLG` now means: this sector is being retried at normal
speed. The 1K font area is no longer part of the file, so `*=` is
`$F400`.

### 7. -131,13 +132,12

```diff
 TITLE                           ; 20 characters
         .SBYTE "   sectorcopy "
-        .BYTE $51,$4E,$54,$00,$00,$00
-CREDIT                          ; "(P) 06/87  E.REUSS"
+        .SBYTE +$40,"1.5"
+        .BYTE $00,$00,$00
+CREDIT                          ; "(C) 07/88 bibosoft"
         .BYTE $80
-        .SBYTE +$C0,"(P)"
-        .BYTE $80
-        .SBYTE +$C0,"06/87"
-        .BYTE $80,$80
-        .SBYTE +$C0,"E.REUSS"
+        .SBYTE +$C0,"(C)"
         .BYTE $80
+        .SBYTE +$C0,"07/88"
+        .SBYTE +$80," bibosoft "
 DASHES
         .REPT 20
```

**Comment:** Title shows version "1.5" (colour 1 characters); the
credit line is now "(C) 07/88 bibosoft" instead of "(P) 06/87
E.REUSS".

### 8. -261,5 +261,5

```diff
 SETTOP
         STA RAMTOP
-        LDA #$01        ; look for the first drive from D1: up
+        LDX #$01        ; look for the first drive from D1: up
         JSR FINDDRIVE
         BCC GOTSOURCE
```

**Comment:** `FINDDRIVE` now gets the start unit in X, not A.

### 9. -278,7 +278,6

```diff
         DEX
         BNE DRVDELAY
+        INC DUNIT       ; look for a second drive after the source
         LDX DUNIT
-        INX             ; look for a second drive after the source
-        TXA
         JSR FINDDRIVE
         BCS ONEDRIVE
```

**Comment:** Searching the second drive: `INC DUNIT / LDX DUNIT`
replaces `LDX / INX / TXA`, because the unit goes in X.

### 10. -360,5 +359,5

```diff
         .SBYTE ".Von Ramdisk schreiben"
         NOP
-        JMP OPTSELECT
+        BEQ OPTSELECT
 OPTSWAP
         LDA SRCDRV
```

**Comment:** `JMP` replaced by `BEQ`: Z is still set from the end of
the inline text (shorter, same effect).

### 11. -466,8 +465,8

```diff
         EOR DSTDRV
         STA TWODRV         ; TWODRV = 0: source and target are the same drive
-        LDY #$06
         LDA #$00
         STA SLOWFLG         ; SLOWFLG = 0: high speed fallback not used yet
         STA TGTFMTD         ; TGTFMTD = 0: target not formatted yet
+        LDY #$06
 CLRBARS
         STA RBARPOS,Y     ; clear both progress bar counters RBARPOS-WBARCNT
```

**Comment:** `LDY #$06` moved behind the two stores; no change in effect.

### 12. -496,5 +495,4

```diff
         BEQ PROMPT1DRV
         LDX #<MSGINSERT ; "DISKETTEN EINLEGEN" (two drives)
-        LDA #$20
 PROMPT
         STX MSGLMS      ; select the message line in the display list
```

**Comment:** Removed a useless `LDA #$20` before the `PROMPT` label
(it was reloaded right after).

### 13. -517,4 +515,13

```diff
 ; SECSTEP = sectors per progress bar step.
 GETDENS
+        LDA #$00        ; first pass: clear the sector map
+        TAX
+CLRMAP
+        STA SECMAP,X
+        INX
+        CPX #$82
+        BCC CLRMAP
+        LDA #$A8
+        STA SIOSND
         LDA #$53        ; command $53 STATUS, 4 bytes into $0400
         STA DCOMND
```

**Comment:** New: in the first pass the sector map (130 bytes at
`$037D`, one bit for each of up to 1040 sectors) is cleared, and
`SIOSND` is set to `$A8` for the STATUS command.

### 14. -533,16 +540,13

```diff
         AND #$A0
         STA DENSITY
-        AND #$80
-        BNE DENSMED
+        BMI DENSMED
         LDA #$05
         STA SECSTEP
-        LDA SECBUF
-        AND #$20
+        LDA DENSITY
         BNE DENSDBL
-        STA DENSITY
         JSR PRINTI
         .SBYTE "SINGLE"
         NOP
-        JMP PREFORMAT
+        BEQ PREFORMAT
 DENSMED
         LDX #$08
```

**Comment:** Density test shortened: `STA DENSITY` already sets N for
medium density, so `BMI` replaces `AND #$80 / BNE`; single/double is
decided from `DENSITY` instead of reloading the buffer; the `JMP`
became a `BEQ`. Result unchanged.

### 15. -594,11 +598,13

```diff
         LDY SRCDRV
         STY DUNIT         ; unit = source drive
-        BIT SLOWFLG         ; after a read error the source drive stays at
-        BPL READSTART
-        LDA #$28        ; normal speed for the rest of the copy
-        STA DRVSPD,Y
-READSTART
+        LDA DRVSPD,Y    ; remember its high speed divisor, it is put
+        STA SAVSPD      ; back before every sector
         JSR BUFRESET    ; buffer pointer to $0400, main memory
+        LDA #$A8
+        STA SIOSND
 READLOOP
+        LDY DUNIT       ; every sector starts at high speed again
+        LDA SAVSPD
+        STA DRVSPD,Y
         LDX RBARPOS
         LDY RBARQ
```

**Comment:** The source drive's high speed divisor is saved in
`SAVSPD` at the start of the read phase and written back to `DRVSPD`
before every sector (new first lines of `READLOOP`). Before, a failed
read switched the source to normal speed for the rest of the
pass. `SIOSND` is set to `$A8` for the read.

### 16. -622,6 +628,7

```diff
         JSR SIOTRY2     ; do the SIO call (2 tries)
         BCC READNEXT    ; ok: next sector
-        BIT SLOWFLG         ; already at normal speed: report the error
+        LDA SLOWFLG         ; already at normal speed: report the error
         BPL SLOWDOWN
+        STA EMPTY       ; unreadable sector: keep it as if it had data
         JSR DISKERR     ; "DISK FEHLER #xx", wait for a key
         CMP #$06
```

**Comment:** After a failed read at normal speed the error flag
`EMPTY` is set to `$FF` (A holds `SLOWFLG`), so the unreadable sector
counts as a sector with data and takes buffer space.

### 17. -629,12 +636,13

```diff
         CMP #$05
         BEQ READNEXT    ; SELECT: skip this sector
-        JMP MENULOW     ; OPTION: abort, back to the menu
+        LDY DUNIT       ; OPTION: abort, back to the menu with the
+        LDA SAVSPD      ; high speed divisor put back
+        STA DRVSPD,Y
+        JMP MENULOW

-; First read error: fall back from high speed to normal speed (19200 baud)
-; for the source drive and retry. The old divisor is kept in SAVSPD.
+; Read error at high speed: fall back to normal speed (19200 baud) for this
+; one sector and retry. The old divisor is kept in SAVSPD.
 SLOWDOWN
         LDY DUNIT
-        LDA DRVSPD,Y
-        STA SAVSPD
         LDA #$28
         STA DRVSPD,Y
```

**Comment:** OPTION (abort) now puts the high speed divisor back
before returning to the menu. The fallback no longer saves the divisor
(it is saved at the start of the pass), it only sets 19200 baud for
this one sector.

### 18. -642,4 +650,7

```diff
         BNE READSECT
 READNEXT
+        LDA #$00
+        STA SLOWFLG
+        JSR MARKSEC     ; note in the sector map whether it has data
         JSR NEXTSECT    ; next sector / buffer address
         BCC READLOOP    ; loop until disk end or buffer full
```

**Comment:** After each sector (read ok or skipped): `SLOWFLG` is
cleared again, so the next sector tries high speed first, and
`MARKSEC` records in the sector map whether the sector had data.

### 19. -666,7 +677,5

```diff
         JMP WRITEPASS
 CHKABORT
-        CMP #$03        ; OPTION: abort
-        BNE WRITEPASS
-        JMP MENULOW
+        JMP MENULOW     ; OPTION: abort

 ; --------------------------------------------------------------------------
```

**Comment:** After the target prompt only OPTION is left over for
`CHKABORT`: every key below 5 leads straight to the menu (the compare
with 3 is gone).

### 20. -681,9 +690,4

```diff
         LDA DSTDRV
         STA DUNIT         ; unit = target drive
-        BIT SLOWFLG
-        BPL CHKFORMAT
-        LDY SRCDRV         ; source fell back to normal speed: put its
-        LDA SAVSPD         ; high speed divisor back
-        STA DRVSPD,Y
 CHKFORMAT
         LDA WPASS         ; format only before the first write pass,
```

**Comment:** The block that restored the high speed divisor of the
source before writing is gone; it is restored for every sector in the
read loop now.

### 21. -699,18 +703,11

```diff
         LDX #<MSGFORMAT ; "FORMATIEREN"
         STX MSGLMS
-        LDA DSTFAST
-        BPL FMTSETCMD   ; high speed target: set density (PERCOM) first
-        JSR SENDPERCOM
-FMTSETCMD
+        JSR SENDPERCOM  ; set the density (PERCOM) first
         LDA #$80
         STA DBYT
         LDA #$22        ; command $22: format medium density
-        BIT DENSITY
+        LDX DENSITY
         BMI FMTSEND
-        LDA #$80
-        STA DBYT
-        LDA DENSITY
         BEQ FMTSD
-        BMI FMTSD
         ASL DBYT
 FMTSD
```

**Comment:** Formatting: the PERCOM density block is now sent to the
target always (before: only to high speed
drives). Medium/single/double selection simplified (`LDX DENSITY` sets
the flags, no double load of `DBYT`).

### 22. -718,4 +715,6

```diff
 FMTSEND
         STA DCOMND
+        LDA #$A8
+        STA SIOSND
         LDA #$D5        ; bad sector list goes to $D500
         STA DBUF+1
```

**Comment:** `SIOSND` = `$A8` for the format command.

### 23. -724,6 +723,5

```diff
         LDY DSTDRV
         JSR SIOSLOW     ; SIO call at normal speed
-        TYA
-        BPL WRITESTART
+        BCC WRITESTART
         JSR DISKERR     ; error: "DISK FEHLER", retry
         BCC FORMAT
```

**Comment:** `SIOSLOW` returns the SIO result in carry, so `BCC`
replaces `TYA / BPL`.

### 24. -734,4 +732,6

```diff
         INC WPASS         ; count the write pass
         JSR BUFRESET    ; buffer pointer back to $0400, main memory
+        LDA #$A8
+        STA SIOSND
 WRITESECT
         LDX #<MSGSECTOR
```

**Comment:** `SIOSND` = `$A8` at the start of the write phase.

### 25. -744,6 +744,10

```diff
         STA DAUX+1
         JSR SETLEN      ; byte count (128/256), show sector number
-        JSR ISEMPTY     ; freshly formatted and sector all zero:
-        BCS WRITENEXT   ; nothing to write, skip it
+        JSR GETMARK     ; EMPTY = sector map bit: does the sector have data?
+        LDA NOFMT       ; freshly formatted and sector all zero:
+        BNE DOWRITE
+        LDA EMPTY
+        BEQ WRITENEXT   ; nothing to write, skip it
+DOWRITE
         JSR SIOTRY2     ; do the SIO call (2 tries)
         BCC WRITENEXT
```

**Comment:** Writing: `ISEMPTY` (which scanned the buffer) is replaced
by the sector map. `GETMARK` sets `EMPTY` from the map. If the target
was not formatted (`NOFMT <> 0`) every sector is written, else sectors
without data are skipped.

### 26. -766,6 +770,10

```diff
         LDA #$51        ; high speed target: command $51 (flush the
         STA DCOMND
-        LDA #$00        ; drive's write buffer)
-        STA DSTATS
+        LDY #$00        ; drive's write buffer)
+        STY DSTATS
+        STY SIOSND
+        DEY
+        STY DAUX
+        STY DAUX+1
         LDY DSTDRV
         JSR SIOSLOW
```

**Comment:** Command `$51` (flush) gets aux `$FFFF` and `SIOSND` = 0
(silent). `DSTATS` = 0 is now stored through Y.

### 27. -811,4 +819,6

```diff
         LDA #$80
         STA DSTATS
+        ASL A
+        STA SIOSND
         LDY DSTDRV
         JMP SIOSLOW
```

**Comment:** PERCOM (`$4F`) is sent with `SIOSND` = 0: `ASL A` turns
the `$80` direction byte into 0.

### 28. -823,4 +833,5

```diff
         STA DAUX
         LDA #$00
+        STA SIOSND
         STA DSTATS
         LDA #$44
```

**Comment:** Command `$44` is sent with `SIOSND` = 0.

### 29. -943,5 +954,6

```diff
 ; Advance to the next sector and buffer position.
 ; Last sector is 720 ($2D0), or 1040 ($410) for medium density.
-; The buffer pointer DBUF moves up by the byte count and skips over the
+; The buffer pointer DBUF moves up by the byte count (only when the sector
+; has data, EMPTY <> 0; empty sectors are not stored) and skips over the
 ; memory that cannot be used:
 ;   main RAM $0400 up to RAMTOP (cartridge), $C000-$CFFF, $D800-$EFFF,
```

**Comment:** Comment only: `NEXTSECT` moves the buffer pointer only
for sectors with data.

### 30. -976,4 +988,6

```diff
         INC SECTOR+1
 NEXTBUF
+        LDA EMPTY       ; sector without data: it takes no buffer space
+        BEQ BUFOK
         LDA DBUF
         CLC
```

**Comment:** New: `NEXTBUF` skips the pointer update when `EMPTY =
0`. Sectors that are all zero are not stored in the buffer, so more
sectors fit into one pass.

### 31. -994,4 +1008,8

```diff
         BNE BUFOK
         LDA #$C0
+        BNE SETHI
+SKIPIO
+        LDA #$D8
+SETHI
         STA DBUF+1
         LDA #$00
```

**Comment:** The cartridge and I/O skips share one tail (`SETHI`):
only the high byte differs (`$C0` or `$D8`), the low byte is 0 in both
cases.

### 32. -1000,11 +1018,4

```diff
         CLC
         BCC BUFRET
-SKIPIO
-        LDA #$00
-        STA DBUF
-        LDA #$D8
-        STA DBUF+1
-        CLC
-        BCC BUFRET
 MAINFULL
         LDA NUMBANKS         ; no extended RAM: buffer full
```

**Comment:** The old separate `SKIPIO` code is removed (merged into
`SETHI` above).

### 33. -1142,26 +1153,50

```diff

 ; --------------------------------------------------------------------------
-; C = 1 if the target was formatted ("Formatieren: JA") and the sector in
-; the buffer is all zero, so it need not be written.
-; --------------------------------------------------------------------------
-ISEMPTY
-        LDA NOFMT
-        BNE NOTEMPTY
-        LDA DBUF
-        STA EMPTYLP+1
-        LDA DBUF+1
-        STA EMPTYLP+2
-        LDY #$00
-EMPTYLP
-        LDA $AAAA,Y     ; address patched above
-        BNE NOTEMPTY
-        INY
-        CPY DBYT
-        BNE EMPTYLP
-        SEC
-        RTS
-NOTEMPTY
-        CLC
+; Sector map: one bit per sector at SECMAP (sector DAUX is bit 7-(DAUX and 7)
+; of byte DAUX/8). 1 = the sector has data, 0 = all zero.
+; MARKSEC: after a read, set the bit if EMPTY <> 0.
+; GETMARK: before a write, EMPTY = the sector's bit.
+; --------------------------------------------------------------------------
+MARKSEC
+        LDA DAUX        ; X = DAUX and 7 (bit), Y = DAUX / 8 (byte);
+        AND #$07        ; the high byte is shifted along and restored
+        TAX
+        LDA DAUX
+        LSR DAUX+1
+        ROR A
+        LSR DAUX+1
+        ROR A
+        LSR DAUX+1
+        ROR A
+        TAY
+        LDA SECTOR+1
+        STA DAUX+1
+        LDA EMPTY
+        BEQ MARKNO
+        LDA BITMASKS,X
+MARKNO
+        ORA SECMAP,Y
+        STA SECMAP,Y
+        RTS
+GETMARK
+        LDA DAUX        ; X = DAUX and 7 (bit), Y = DAUX / 8 (byte);
+        AND #$07        ; the high byte is shifted along and restored
+        TAX
+        LDA DAUX
+        LSR DAUX+1
+        ROR A
+        LSR DAUX+1
+        ROR A
+        LSR DAUX+1
+        ROR A
+        TAY
+        LDA SECTOR+1
+        STA DAUX+1
+        LDA SECMAP,Y
+        AND BITMASKS,X
+        STA EMPTY
         RTS
+BITMASKS
+        .BYTE $80,$40,$20,$10,$08,$04,$02,$01
 PRINTI
         PLA
```

**Comment:** `ISEMPTY` removed. New `MARKSEC` and `GETMARK` with the
table `BITMASKS` keep one bit per sector in `SECMAP`: byte = sector /
8, bit = 7 - (sector and 7). The sector number's high byte is shifted
along and restored from `SECTOR+1`.

### 34. -1206,10 +1241,9

```diff
         CPY #$E0
         BNE BEEPLP
-        JSR GETKEY
-        RTS
 GETKEY
         LDA CONSOL
         CMP #$07
         BNE GETKEY
+KEYRELEASED
         LDX #$00
 KEYDEBNC
```

**Comment:** `BEEPKEY` falls through into `GETKEY` (the `JSR / RTS`
pair is gone). New label `KEYRELEASED` as restart point of the
debounce.

### 35. -1221,4 +1255,9

```diff
         CMP #$07
         BEQ KEYWAIT
+KEYSTABLE
+        CMP CONSOL      ; the same key for 256 reads, else start over
+        BNE KEYRELEASED
+        DEX
+        BNE KEYSTABLE
         LDY #$40
 KEYCLICK
```

**Comment:** Debounce: after a key is seen, `CONSOL` must read the
same value 256 times in a row, otherwise the routine starts again from
the release wait.

### 36. -1227,9 +1266,8

```diff
         DEY
         BNE KEYCLICK
-        STY ATRACT
         RTS

 ; --------------------------------------------------------------------------
-; Find a drive, starting at unit A (up to D4:). Sends command $3F (ask for
+; Find a drive, starting at unit X (up to D4:). Sends command $3F (ask for
 ; the high speed index) and stores the answer as the drive's POKEY divisor.
 ; Out: C = 1 no drive found
```

**Comment:** `STY ATRACT` removed (the OS is not running). Comment: `FINDDRIVE` takes the unit in X.

### 37. -1237,21 +1275,23

```diff
 ; --------------------------------------------------------------------------
 FINDDRIVE
-        STA DUNIT
+        STX DUNIT
+        LDA #$A8
+        STA SIOSND
         LDA #$3F        ; command $3F: get high speed index, 1 byte
         STA DCOMND
         LDX #$00
+        STX DBUF        ; the answer goes to $0000 (HSIDX)
+        STX DBUF+1
         INX
         STX DBYT
         LDA #$40
         STA DSTATS
-        JSR BUFRESET
         JSR SIO
-        TYA
         BPL DRVFAST
-        CMP #$8B        ; NAK: a drive without high speed
+        CPY #$8B        ; NAK: a drive without high speed
         BEQ DRVNORMAL
         INC DUNIT
-        LDA DUNIT
-        CMP #$05
+        LDX DUNIT
+        CPX #$05
         BCC FINDDRIVE
         SEC
```

**Comment:** `FINDDRIVE`: unit in X, `SIOSND` = `$A8`, the answer
buffer is `$0000` (`DBUF` = 0) instead of `BUFRESET` / `$0400`. The
result of `SIO` is tested in the flags (SIO now ends with `LDY
SIOSTAT`), `TYA` is dropped, and the loop counter uses X.

### 38. -1262,5 +1302,5

```diff
         RTS
 DRVFAST
-        LDA SECBUF
+        LDA HSIDX
         LDY DUNIT
         STA DRVSPD,Y     ; high speed POKEY divisor for this drive
```

**Comment:** The high speed index is read from `$00` (`HSIDX`).

### 39. -1301,8 +1341,7

```diff
         STA SIOSTAT
         STA NORETRY
+        STA FRMPTR+1
         LDA #<CMDFRM
         STA FRMPTR
-        LDA #>CMDFRM
-        STA FRMPTR+1
         LDA #$04
         STA FRMLEN
```

**Comment:** SIO: the command frame is in zero page, so only the low
pointer byte is loaded (`FRMPTR+1` = 0 from the accumulator).

### 40. -1326,9 +1365,8

```diff
         JSR RECVFRAME
 SIOEXIT
+        JSR TIMSTOP
+        STX IRQEN       ; X = 0: no POKEY interrupts
         LDA #$A0
         STA AUDC4
-        LDA POKMSK
-        STA IRQEN
-        JSR TIMSTOP
         LDY SIOSTAT
         STY DSTATS
```

**Comment:** SIO exit: the timer is stopped first, which leaves X = 0;
`STX IRQEN` then disables all POKEY interrupts (before: restored from
`POKMSK`).

### 41. -1336,25 +1374,34

```diff

 ; Send a frame (FRMPTR = data, FRMLEN = length) plus checksum, then wait for
-; the drive's ACK.
+; the drive's ACK. A sector of 128/256 bytes (FRMLEN = $80 or $00) with
+; EMPTY = 0 is sent as zeros without reading the buffer.
 SENDFRAME
-        LDX #$FF
+        LDY #$80
 SENDDLY
-        DEX
+        INY
         BNE SENDDLY
         LDA #$23
         JSR SERINIT
-        LDY #$00
+SENDNEXT
+        LDA FRMLEN
+        BMI SENDSECT
+        BNE SENDFETCH
+SENDSECT
+        LDA EMPTY
+        BEQ SENDBYTE
+SENDFETCH
         LDA (FRMPTR),Y
+SENDBYTE
+        CPY #$00
+        BNE SENDOTHER
         STA CHKSUM
         STA SEROUT
-SENDLP
+        BEQ SENDADV
+SENDOTHER
+        JSR PUTBYTE
+SENDADV
         INY
         CPY FRMLEN
-        BEQ SENDSUM
-        LDA (FRMPTR),Y
-        JSR PUTBYTE
-        JSR ADDSUM
-        JMP SENDLP
-SENDSUM
+        BNE SENDNEXT
         LDA CHKSUM
         JSR PUTBYTE
```

**Comment:** `SENDFRAME` rewritten: shorter start delay; the first
byte and the other bytes go through one loop (the first byte starts
the checksum, the others call `PUTBYTE`, which now adds to the
checksum itself). New: a data frame of 128 or 256 bytes with `EMPTY =
0` sends zeros without reading the buffer, so sectors without data
need no buffer space also when writing to an unformatted target.

### 42. -1363,19 +1410,25

```diff
         AND #$08
         BNE SENDWAIT
-        LDX #$00
-        LDY #$03
-        JSR TIMSET
-        LDA #$C0
         STA IRQEN
+        LDX #$00        ; (redundant: TIMSETY clears X again)
+        LDY #$03
+        JSR TIMSETY     ; wait for the ACK, 3 frames
         JMP WAITACK

 ; Receive a data frame (FRMPTR, FRMLEN bytes) and compare the checksum.
+; EMPTY = OR of all received bytes.
 RECVFRAME
-        LDA #$00
-        STA CHKSUM
+        LDY #$32
+        JSR TIMSETY     ; timeout 50 frames
         LDY #$00
+        STY CHKSUM
+        STY EMPTY
 RECVLP
         JSR GETBYTE
         STA (FRMPTR),Y
+        TAX
+        ORA EMPTY
+        STA EMPTY
+        TXA
         JSR ADDSUM
         INY
```

**Comment:** After the send: IRQEN is switched off with the
accumulator (0) instead of `$C0`; the ACK wait uses
`TIMSETY`. `RECVFRAME` sets a 50 frame timeout for the data, clears
`CHKSUM` and `EMPTY`, and ORs every received byte into
`EMPTY`. Therefore `EMPTY` is the "sector has data" flag after a read.

### 43. -1392,4 +1445,5

```diff
 SIOERROR
         STA SIOSTAT
+        JSR TIMSTOP
         LDX SIOSTK
         TXS
```

**Comment:** `SIOERROR` stops the timeout timer before it unwinds the stack.

### 44. -1402,14 +1456,12

```diff
         JMP SIOEXIT

-; Wait for "complete" after a command; format commands (< $50) get a long
+; Wait for "complete" after a command; format commands (< $30) get a long
 ; timeout. 'A'/'C' = ok, 'E' = device error ($90), else NAK ($8B).
 WAITCOMPL
-        LDX DCOMND
-        CPX #$50
-        BCS SHORTTMO
-        LDX #$0A
-        BNE STARTTMO
-SHORTTMO
         LDX #$01
+        LDA DCOMND
+        CMP #$30
+        BCS STARTTMO
+        LDX #$0C
 STARTTMO
         LDY #$60
```

**Comment:** `WAITCOMPL`: only commands below `$30` (format `$20-$22`)
get the long timeout (before: below `$50`, which also covered `$3F`,
`$44`, `$4F`); the long timeout is 12*256+96 frames, before 10*256+96.

### 45. -1433,8 +1485,10

```diff
         STA SIOSTAT

-; Stop the timeout timer / start it with X*256+Y frames. On expiry the NMI
-; handler jumps through TIMVEC to SIOTMOUT (timeout error).
+; Stop the timeout timer / start it with X*256+Y frames (TIMSETY: Y frames).
+; On expiry the NMI handler jumps through TIMVEC to SIOTMOUT (timeout
+; error). Out: X = 0 for TIMSTOP.
 TIMSTOP
         LDY #$00
+TIMSETY
         LDX #$00
 TIMSET
```

**Comment:** `TIMSETY` is a new entry point of the timer routine (X =
0, Y = frames).

### 46. -1443,22 +1497,8

```diff
         LDA #>SIOTMOUT
         STA TIMVEC+1
-        TXA
-        LDX #$03
-TIMSETLP
-        STA WSYNC
-        DEX
-        BNE TIMSETLP
-        STA TIMER+1
+        STX TIMER+1
         STY TIMER
         RTS

-; Add A to the frame checksum CHKSUM (with end around carry).
-ADDSUM
-        CLC
-        ADC CHKSUM
-        ADC #$00
-        STA CHKSUM
-        RTS
-
 ; Wait for and return one received byte; framing/overrun error -> SIOTMOUT.
 GETBYTE
```

**Comment:** `TIMSET` no longer waits 3 lines with `WSYNC`; it just
stores X and Y. `ADDSUM` moved behind `PUTBYTE`.

### 47. -1466,31 +1506,33

```diff
         AND #$20
         BNE GETBYTE
-        LDA #$DF
         STA IRQEN
-        LDA #$F8
+        LDA #$38
         STA IRQEN
         LDA SKSTAT
         STA SKRES
-        BPL GETBYTEERR
+        BPL SIOTMOUT
         AND #$20
-        BEQ GETBYTEERR
+        BEQ SIOTMOUT
         LDA SERIN
         RTS
-GETBYTEERR
-        JMP SIOTMOUT

-; Send one byte as soon as POKEY is ready.
+; Send byte A as soon as POKEY is ready and add it to the checksum.
 PUTBYTE
-        PHA
+        TAX
 PUTBYTELP
         LDA IRQST
         AND #$10
         BNE PUTBYTELP
-        LDA #$EF
         STA IRQEN
-        LDA #$F8
+        LDA #$38
         STA IRQEN
-        PLA
+        TXA
         STA SEROUT
+; Add A to the frame checksum CHKSUM (with end around carry).
+ADDSUM
+        CLC
+        ADC CHKSUM
+        ADC #$00
+        STA CHKSUM
         RTS
```

**Comment:** `GETBYTE`: POKEY IRQ enable is `$38` (serial input
interrupts) after a 0 write, a framing error branches directly to
`SIOTMOUT` (no more `GETBYTEERR`). `PUTBYTE` keeps the byte in X
instead of the stack and falls through into `ADDSUM`, so it also
updates the checksum.

### 48. -1501,7 +1543,7

```diff
         LDA #$28
         STA AUDCTL
-        LDA #$A8
+        LDA SIOSND
         STA AUDC4
-        LDA #$F8
+        LDA #$38
         STA IRQEN
         RTS
```

**Comment:** `SERINIT` uses `SIOSND` for AUDC4 and `$38` for IRQEN.

### 49. -1509,36 +1551,33

```diff
 ; --------------------------------------------------------------------------
 ; NMI: RESET key restarts via $0100, VBI counts down the SIO timeout timer.
+; Shift+Control+Tab (KBCODE $EC) leaves to the OS through the loader stub.
 ; --------------------------------------------------------------------------
 NMI
         PHA
         LDA NMIST
+        STA NMIRES
         AND #$20
         BEQ NMIVBI
         JMP RESTART
 NMIVBI
-        TXA
-        PHA
-        TYA
-        PHA
-        STA NMIRES
-        LDY TIMER
+        LDA TIMER
         BNE TIMDEC
-        LDY TIMER+1
-        BEQ NMIEXIT
+        LDA TIMER+1
+        BEQ NMIKEY
         DEC TIMER+1
 TIMDEC
         DEC TIMER
+        BNE NMIKEY
+        LDA TIMER+1
+        BEQ TIMEXPIRED
+NMIKEY
+        LDA KBCODE
+        CMP #$EC
         BNE NMIEXIT
-        LDY TIMER+1
-        BNE NMIEXIT
-        JSR TIMEXPIRED
+        JMP OSEXIT
 NMIEXIT
         LDA #$08
         STA CONSOL
         PLA
-        TAY
-        PLA
-        TAX
-        PLA
         RTI
 TIMEXPIRED
```

**Comment:** NMI handler: it clears the NMI request (`STA NMIRES`) at
once and only uses A, so X and Y are not saved. A timer that runs out
jumps through `TIMVEC` directly (the stack is reset by `SIOTMOUT`
anyway). New: when `KBCODE` is `$EC` (Shift+Control+Tab) it jumps to
`OSEXIT` (`$013E`) and leaves the program.

### 50. -1546,7 +1585,4

```diff
 IRQ
         PHA
-        LDA IRQST
-        EOR #$FF
-        STA IRQEN
         LDA #$00
         STA IRQEN
```

**Comment:** IRQ handler: just disables all POKEY interrupts (the
read-and-invert of `IRQST` is gone).

### 51. -1566,8 +1602,5

```diff
         .ENDR
 SAVEDBARS
-        .REPT 142
+        .REPT 80
         .BYTE $00
         .ENDR
-        .WORD NMI       ; $FFFA NMI vector
-        .WORD $0000     ; $FFFC RESET vector (unused)
-        .WORD IRQ       ; $FFFE IRQ vector
```

**Comment:** `SAVEDBARS` is 80 bytes (the saved progress lines,
`$78-$C7`) and the vectors are no longer part of this file; the loader
file writes them at `$FFFA`.
