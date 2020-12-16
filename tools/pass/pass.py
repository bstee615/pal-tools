#!/bin/python3

from mylog import log
import argparse

args = parse_args()
verbose=False

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    arguments = parser.parse_args()
    
    if arguments.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    return arguments

def main():
    print('TODO passify the things')

if __name__ == '__main__':
    main()
