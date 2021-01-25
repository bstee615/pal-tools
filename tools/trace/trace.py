#!/bin/python3

from mylog import log
import argparse
import logging
import nodeutils
from clang.cindex import CursorKind
from pathlib import Path
import subprocess
from collections import defaultdict, namedtuple
import itertools
import sys
from .pin import Pin
from .location import Location

def parse_args():
    file_dir = Path(__file__).parent
    default_pinroot = str(file_dir / 'pin-3.16')

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)', default='WARN')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    parser.add_argument('-p', '--pin-root', type=str, help=f'Use an alternative path to Pin root. Default: {default_pinroot}', default=default_pinroot)
    parser.add_argument('-o', '--output-file', type=str, help='Output to a file')
    parser.add_argument('target', help='Target command to trace. Must contain debug info (compiled with -g -O0).', nargs='*')
    arguments = parser.parse_args()
    
    if arguments.log_level:
        log.setLevel(logging.getLevelName(arguments.log_level))
    
    if arguments.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    if arguments.pin_root:
        arguments.pin_root = Path.cwd() / arguments.pin_root

    arguments.pin = Pin.do_wizard(arguments.pin_root, file_dir / 'install.sh')

    return arguments

args = parse_args()
verbose=False

def debug_print_code(locations):
    """
    Print the source lines from a list of locations on the debug stream.
    """
    locations_by_filename = defaultdict(list)
    for l in locations:
        locations_by_filename[l.filepath].append(l.lineno)
    for filepath, linenos in locations_by_filename.items():
        log.debug(filepath)
        filelines = Path(filepath).read_text().splitlines()
        for l in sorted(linenos):
            log.debug(f'{l:4} {filelines[l-1]}')

def main():
    target = Path(args.target[0])
    target_args = args.target[1:]
    dynamic_locations = args.pin.run(target, target_args)
    log.debug(f'{len(dynamic_locations)} logs')
    for l in dynamic_locations:
        log.debug(l)

    static_locations = []
    logged_filenames = set(l.filepath for l in dynamic_locations)
    for f in logged_filenames:
        log.debug(f'Parsing source file {f}')
        root = nodeutils.parse(f)
        kinds = [CursorKind.VAR_DECL, CursorKind.CASE_STMT, CursorKind.DEFAULT_STMT]
        nodes = list(itertools.chain.from_iterable(nodeutils.find(root, k) for k in kinds))
        locations = [Location(n.location.file.name, n.location.line) for n in nodes]
        log.debug(f'{len(locations)} locations for source file {f}')
        for l in locations:
            log.debug(l)
        static_locations += locations

    # Output trace locations to file
    unique_dynamic_locations = set(dynamic_locations)
    unique_static_locations = set(static_locations)
    all_locations = unique_dynamic_locations.union(unique_static_locations)
    log.debug(f'Removed {len(dynamic_locations) - len(unique_dynamic_locations)} duplicate dynamic locations')
    log.debug(f'Removed {len(static_locations) - len(unique_static_locations)} duplicate static locations')
    log.debug(f'Added {len(all_locations) - len(unique_dynamic_locations)} static locations to {len(unique_dynamic_locations)} dynamic locations totaling {len(all_locations)}')
    if args.output_file:
        output_stream = open(args.output_file, 'w')
    else:
        output_stream = sys.stdout
    for l in all_locations:
        output_stream.write(f'{l.filepath}:{l.lineno}\n')
    if output_stream is not sys.stdout:
        output_stream.close()

    debug_print_code(all_locations)

if __name__ == '__main__':
    main()

