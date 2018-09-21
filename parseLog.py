
import os

import argparse


parser = argparse.ArgumentParser(description='PyTorch Cifar10 Training')
parser.add_argument('-f', help='filename', action='store')

args = parser.parse_args()


def show(filename):
	if os.path.isfile(filename):
		acc = []
		infile = open(filename, 'r')
		content = infile.readlines()
		for line in content:
			elements = line.split('* Prec') 
			if len(elements) > 1:
				acc.append(float((elements[1].strip('% \n'))))
		print('max val acc before 200:',max(acc[:200]))
		print('max val acc:',max(acc))

if __name__=='__main__':
    show(args.f)

