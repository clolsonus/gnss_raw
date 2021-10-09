This area is a very much a work in progress (or a sandbox if you will.)

Starting out (as of Oct 9, 2021) I have just a single script.  It uses
the laika python package to compute satellite locations (using either
the ephemeris downloaded from the interweb, or a set of interpolated
(precomputed) locations also downloaded from the interweb.  The script
read the raw pseudoranges from a ublox9 (using gpsd as the
intermediate interface.)  For initial tests I am seeing results in the
5-10m errror relative to the receivers own internal/proprietary
solution.  This also uses the UMN NavPy package (which you can google
for) to compute lla2ecef because the receiver is reporting it's
internal solution in LLA and the raw solution is in ECEF.