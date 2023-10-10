#!env python3

import csv
import argparse

#
# Parse arguments
#

parser = argparse.ArgumentParser( prog = 'etherwav', description = 'Decode 10BASE-T ethernet frames from OWON HDS272S CSV exports' )
parser.add_argument( 'filename' )
parser.add_argument( '-t', '--threshold', type = float, default = -500, help = 'First zero crossing threshold, should be negative' )
parser.add_argument( '-s', '--sample-rate', type = float, default = 250, help = 'Sample rate in MSa/s' )

args = parser.parse_args()

#
# Collect datapoints
#

datapoints = []
bits = []

with open( args.filename, newline = '' ) as csvfile:
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

while pos < len( datapoints ):
	if datapoints[ pos ] <= args.threshold:
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
# Find zero crossings and output bits.  Zero crossing direction is determined by the slope of the line
# across 3 datapoints at samples_per_bit.  Position ambiguity is resolved by resynchronizing to the closest
# actual zero crossing after each bit.
#

samples_per_bit = args.sample_rate / 10.0

while pos < len( datapoints ):
	pos = pos + int( samples_per_bit )
	if pos > len( datapoints ):
		break

	if datapoints[ pos - 1 ] == 0 and datapoints[ pos ] == 0:
		print( f"Quiet period detected at offset {pos}, stopping" )
		break

	# Determine the direction at this sample over a range of 3 samples to avoid duplicates
	if datapoints[ pos - 2 ] < datapoints[ pos ]:
		bit = 1
	elif datapoints[ pos - 2 ] > datapoints[ pos ]:
		bit = 0

	bits.append( bit )

	# Attempt to resynchronize at the actual zero crossing datapoint.  Target is the datapoint
	# immediately after the zero crossing

	if bit == 0:
		if datapoints[ pos ] > 0:
			while pos < len( datapoints ) - 1 and datapoints[ pos ] > 0:
				pos = pos + 1
		elif datapoints[ pos ] < 0:
			while pos > 0 and datapoints[ pos - 1 ] < 0:
				pos = pos - 1
	elif bit == 1:
		if datapoints[ pos - 1 ] > 0:
			while pos > 0 and datapoints[ pos - 1 ] > 0:
				pos = pos - 1
		elif datapoints[ pos ] < 0:
			while pos < len( datapoints ) - 1 and datapoints[ pos ] < 0:
				pos = pos + 1

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
