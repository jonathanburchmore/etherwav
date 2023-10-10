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
parser.add_argument( '-m', '--min', type = float, default = 0.60, help = 'Minimum zero crossing spacing, in percent' )
parser.add_argument( '-M', '--max', type = float, default = 1.30, help = 'Maximum zero crossing spacing, in percent' )

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
# Find zero crossings and output bits.  To handle slower sample rates, calculate the "ideal" position of the
# zero crossing based on the number of decoded bits and the starting offset, plus half of the sample size
#

samples_per_bit = args.sample_rate / 10.0
min_spacing = int( samples_per_bit * args.min )
max_spacing = int( samples_per_bit * args.max )

while pos < len( datapoints ):
	pos = pos + min_spacing
	while pos < min( pos + max_spacing, len( datapoints ) ):
		if datapoints[ pos - 1 ] < 0 and datapoints[ pos ] >= 0:
			bit = 1
			break
		elif datapoints[ pos - 1 ] > 0 and datapoints[ pos ] <= 0:
			bit = 0
			break
		elif datapoints[ pos - 1 ] == 0 and datapoints[ pos ] == 0:
			bit = -1
			break;

		pos = pos + 1

	if bit == None:
		print( f"No crossing found for bit {len( bits )}--end of data?" )
		break;
	elif bit == -1:
		print( f"Quiet period detected at offset {pos}, stopping" )
		break

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
