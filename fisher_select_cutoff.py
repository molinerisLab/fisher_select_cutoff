#!/usr/bin/env python3
from __future__ import with_statement

from sys import stdin, stderr, float_info
from optparse import OptionParser
import numpy
from scipy.stats import fisher_exact
#from random import shuffle
#from subprocess import Popen, PIPE
from collections import defaultdict
#from vfork.io.colreader import Reader



def main():
	usage = '''
%prog < STDIN

For each possible cutoff in scores, compute a contingency table of greater / lower / positive / negative and apply a fisher exact test.
Greater and lower are according to the cutoff and the score, positive and negative are according to label given in input.
The pos / neg labels can be given in two different way, standard mode and universe (-u) mode.

# Input

## Standard mode

.META: STDIN
	1	stratum		a test is calcualted for each stratum separately
	2	score		numeric
	3	pos_neg		a label either in {"pos","neg"} or in {0,1}



## Unverse mode

.META: STDIN
	1	stratum		a test is calcualted for each stratum separately
	1	item_id
	2	score		numeric

.META: universe_file
	1	item_id
	3	pos_neg	eiter in {"pos","neg"} or in {0,1}

For each possible cutoff in scores, compute a contingency table of greater / lower / positive / negative and apply a fisher exact test.

# Output

.META: STDOUT
	1	stratum
	2	greater and positive
	3	lower and positive
	4	greater and negative
	5	lower and negative
	6 	oddsratio
	7	pvalue
	8	score

oddsratio is the ratio of greater/lower positive cases, normalized over the same ratio in negative

The calculated odds ratio is different from the one R uses. This scipy implementation returns the (more common) "unconditional Maximum Likelihood Estimate", while R uses the "conditional Maximum Likelihood Estimate".
'''

	parser = OptionParser(usage=usage)
	
	parser.add_option('-a', '--alternative', type=str, dest='alternative', default="two-sided", help='Defines the alternative hypothesis, The following options are available: two-sided, less, greater [default: %default]', metavar='SIDE')
	parser.add_option('-u', '--universe_file', type=str, dest='universe_file', default=None, help='In the urn-ball metaphore this file contains all bals and the respective label (pos or neg) [default: %default]', metavar='UNIVERSE')
	parser.add_option('-e', '--missing_score', type=float, dest='missing_score', default=0, help='The score attributed to items that have no record in stdin for a given stratum [default: %default]', metavar='MISSING_SCORE')
	parser.add_option('-k', '--kill_not_in_universe', dest='kill_not_in_universe', action='store_true', default=False, help='ignore intems in stdin not present in universe [default: %default]')
	parser.add_option('-0', '--avoid_0_pvalue', dest='avoid_0_pvalue', action='store_false', default=True, help='add sys.float_info.min to each pvalue to avoid 0 as possible value [default: %default]')
	#parser.add_option('-p', '--dump-params', dest='params_file', help='some help FILE [default: %default]', metavar='FILE')

	options, args = parser.parse_args()
	
	if len(args) != 0:
		exit('Unexpected argument number.')

	minimun_pvalue=numpy.nextafter(0, 1)#https://stackoverflow.com/questions/38477908/smallest-positive-float64-number better than float_info.min 
	universe={}
	if options.universe_file:
		with open(options.universe_file, mode='rt') as fh:
			for line in fh:
				item_id,pos_neg = line.rstrip().split('\t')
				if pos_neg=="pos":
					pos_neg=1
				if pos_neg=="neg":
					pos_neg=0
				pos_neg=int(pos_neg)
				assert(pos_neg==1 or pos_neg==0)

				if universe.get(item_id,None) is not None:
					raise("Duplicated entry in universe_file")
				universe[item_id]=pos_neg
			
	
	#for id, sample, raw, norm in Reader(stdin, '0u,1s,2i,3f', False):
	data =   defaultdict(lambda: defaultdict(list))
	scores = defaultdict(lambda: defaultdict(float))
	#scores_min=dict()
	#scores_max=dict()

	if options.universe_file is None:
		for line in stdin:
			stratum,score,pos_neg = line.rstrip().split('\t')
			score=float(score)
			if pos_neg=="pos":
				pos_neg=1
			if pos_neg=="neg":
				pos_neg=0
			pos_neg=int(pos_neg)
			assert(pos_neg==1 or pos_neg==0)

			data[stratum][pos_neg].append(score)

			#s=scores_min.get(stratum)
			#if s==None or s>score:
			#	scores_min[stratum]=s
			#s=scores_max.get(stratum)
			#if s==None or s<score:
			#	scores_max[stratum]=s
	else:
		for line in stdin:
			stratum,item_id,score = line.rstrip().split('\t')
			if not options.kill_not_in_universe and universe.get(item_id,None) is None:
				raise ValueError("Item not found in universe ({})".format(item_id))
			score=float(score)
			scores[stratum][item_id]=score
		for stratum in scores.keys():
			for item_id in universe.keys():
				data[stratum][universe[item_id]].append(scores[stratum].get(item_id, options.missing_score))
				
			

			

	for stratum in data.keys():
		scores = data[stratum][0]+data[stratum][1]
		for s in sorted(set(scores)):
			g_p = len([i for i in data[stratum][1] if i>=s])
			g_n = len([i for i in data[stratum][0] if i>=s])
			l_p = len([i for i in data[stratum][1] if i<s])
			l_n = len([i for i in data[stratum][0] if i<s])
			#pseudocounts
			if g_p==0:
				g_p=1
			if g_n==0:
				g_n=1
			if l_p==0:
				l_p=1
			if l_n==0:
				l_n=1
			
			oddsratio, pvalue = fisher_exact([[g_p,g_n],[l_p,l_n]], options.alternative)
			if options.avoid_0_pvalue:
				pvalue += minimun_pvalue

			print("%s\t%s\t%d\t%d\t%d\t%d\t%f\t%g\t%f" % (stratum, s, g_p, l_p, g_n, l_n, oddsratio, pvalue, -1*numpy.sign(oddsratio-1)*numpy.log10(pvalue)))

if __name__ == '__main__':
	main()

