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
parser.add_argument( '-w', '--window', type = int, default = 6, help = 'Zero crossing window size, in samples' )

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
# Sample rate is 250M/sec, so 100ns crossings should occur roughly every 25 samples.
# Find crossings +/- 6 samples of that spacing and output bits
#

samples_per_bit = int( args.sample_rate / 10 )

while True:
	pos = pos + samples_per_bit - args.window

	if pos > len( datapoints ):
		break

	bit = None
	for pos in range( pos, min( pos + int( args.window * 2 ), len( datapoints ) ) ):
		if datapoints[ pos - 1 ] < 0 and datapoints[ pos ] >= 0:
			bit = 1
			break
		elif datapoints[ pos - 1 ] > 0 and datapoints[ pos ] <= 0:
			bit = 0
			break

	if bit == None:
		print( f"No crossing found between {pos - ( args.window * 2 )} and {pos}--end of data?" )
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
