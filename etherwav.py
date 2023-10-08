#!env python3

import csv

#
# Collect datapoints
#

datapoints = []
bits = []

with open( '/home/burch/Desktop/WAVE1.CSV', newline = '' ) as csvfile:
	reader = csv.reader( csvfile, delimiter = ',' )
	past_header = False
	for row in reader:
		if past_header:
			datapoints.append( float( row[ 1 ] ) )
		elif len( row ) and row[ 0 ] == 'index':
			past_header = True

#
# Begin scanning for ethernet preamble: locate first datapoint below threshold
#

pos = 0
threshold = -500

while pos < len( datapoints ):
	if datapoints[ pos ] <= threshold:
		break

	pos = pos + 1

if pos == len( datapoints ):
	print( "Error: Unable to find first datapoint below threshold" )
	exit()

print( f"Threshold at offset {pos}" )

#
# Find first positive zero crossing, output 1 bit
#

while pos < len( datapoints ):
	if datapoints[ pos ] > 0:
		break;

	pos = pos + 1

if pos == len( datapoints ):
	print( "Error: Unable to find first zero crossing" )
	exit()

print( f"First zero crossing at offset {pos}" )

bits.append( 1 )

#
# Sample rate is 250M/sec, so 100ns crossings should occur roughly every 25 samples.
# Find crossings +/- 6 samples of that spacing and output bits
#

while True:
	pos = pos + 25 - 6

	if pos > len( datapoints ):
		break

	bit = None
	for pos in range( pos, pos + 12 ):
		if datapoints[ pos - 1 ] < 0 and datapoints[ pos ] >= 0:
			bit = 1
			break
		elif datapoints[ pos - 1 ] > 0 and datapoints[ pos ] <= 0:
			bit = 0
			break

	if bit == None:
		print( f"No crossing found between {pos - 12} and {pos}--end of data?" )
		break;

	bits.append( bit )

print( f"Total of {len( bits )} bits decoded" )

#
# Validate that data starts with expected ethernet preamble and SFD byte
#

ethernet_preamble = [
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 0,
	1, 0, 1, 0, 1, 0, 1, 1
]

if bits[ :len( ethernet_preamble ) ] != ethernet_preamble:
	print( "Data does not begin with expected ethernet preamble" )
	exit()

bits = bits[ len( ethernet_preamble ): ]

print( f"{len( bits )} packet bits" )

#
# Strip sets of 8 bits off, printing them in reverse order
#

while len( bits ) >= 8:
	octet = bits[ :8 ][ ::-1 ]
	bits = bits[ 8: ]

	stroctet = ''.join( map( str, octet ) )
	print( f"{stroctet} {hex( int( stroctet, 2 ) )}" )
