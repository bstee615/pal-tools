#!/bin/python3

from mylog import log
import argparse
import logging

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    arguments = parser.parse_args()
    
    if arguments.log_level:
        log.setLevel(logging.getLevelName(arguments.log_level))
    
    if arguments.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    return arguments

args = parse_args()
verbose=False

def main():
    print('TODO traceify the things')

if __name__ == '__main__':
    main()

