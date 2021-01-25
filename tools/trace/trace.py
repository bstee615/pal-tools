#!/bin/python3

from mylog import log
import argparse
import logging
import nodeutils
from clang.cindex import CursorKind

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    parser.add_argument('-p', '--pin-root', help='Use an alternative path to Pin root.')
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
    root = nodeutils.parse('test.c')
    vd = nodeutils.find(root, CursorKind.VAR_DECL) + nodeutils.find(root, CursorKind.CASE_STMT) + nodeutils.find(root, CursorKind.DEFAULT_STMT)
    for v in vd:
        log.debug(nodeutils.pp(v))

if __name__ == '__main__':
    main()

