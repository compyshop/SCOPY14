all: check check15

# --- SCOPY14 ---
scopy14rom.bin: scopy14rom.m65
	atasm -r -oscopy14rom.bin scopy14rom.m65

SCOPY14.NEW: scopy14.m65 scopy14rom.bin
	atasm -oSCOPY14.NEW scopy14.m65

check: SCOPY14.NEW
	cmp SCOPY14.COM SCOPY14.NEW && echo "identical to SCOPY14.COM"

# --- SCOPY15 (atasm sorts the segments, segorder.py puts RUNAD last again) ---
scopy15rom.bin: scopy15rom.m65
	atasm -r -oscopy15rom.bin scopy15rom.m65

SCOPY15.NEW: scopy15.m65 scopy15rom.bin segorder.py
	atasm -oSCOPY15.tmp scopy15.m65
	python3 segorder.py SCOPY15.tmp SCOPY15.NEW
	rm -f SCOPY15.tmp

check15: SCOPY15.NEW
	cmp SCOPY15.COM SCOPY15.NEW && echo "identical to SCOPY15.COM"

clean:
	rm -f scopy14rom.bin SCOPY14.NEW scopy15rom.bin SCOPY15.NEW SCOPY15.tmp
