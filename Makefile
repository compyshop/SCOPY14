all: check

scopy14rom.bin: scopy14rom.m65
	atasm -r -oscopy14rom.bin scopy14rom.m65

SCOPY14.NEW: scopy14.m65 scopy14rom.bin
	atasm -oSCOPY14.NEW scopy14.m65

check: SCOPY14.NEW
	cmp SCOPY14.COM SCOPY14.NEW && echo "identical to SCOPY14.COM"

clean:
	rm -f scopy14rom.bin SCOPY14.NEW
