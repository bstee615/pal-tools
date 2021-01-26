#!/bin/python3

from mylog import log
import argparse
import logging
import nodeutils
from clang.cindex import Cursor, CursorKind, File, SourceLocation
from pathlib import Path
from collections import defaultdict
import sys
from .pin import Pin
from .location import Location, SlimLocation

def parse_args(argv=sys.argv, do_wizard=True):
    file_dir = Path(__file__).parent
    default_pinroot = str(file_dir / 'pin-3.16')

    if '--' in argv:
        after_dash = argv[argv.index('--')+1:]
        argv = argv[:argv.index('--')]
    else:
        after_dash = None

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)', default='WARN')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    parser.add_argument('-p', '--pin-root', type=str, help=f'Use an alternative path to Pin root. Default: {default_pinroot}', default=default_pinroot)
    parser.add_argument('-o', '--output-file', type=str, help='Output to a file')
    arguments = parser.parse_args(argv[1:])
    
    if after_dash is None:
        raise argparse.ArgumentTypeError('A delimiter -- before the command is required')

    # arguments.target = arguments.target.split()
    arguments.target = after_dash
    
    if arguments.log_level:
        log.setLevel(logging.getLevelName(arguments.log_level))
    
    if arguments.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    if arguments.pin_root:
        arguments.pin_root = Path.cwd() / arguments.pin_root

    if do_wizard:
        arguments.pin = Pin.do_wizard(arguments.pin_root, file_dir / 'install.sh')
    else:
        arguments.pin = Pin(arguments.pin_root)

    log.debug(f'arguments: {arguments}')

    return arguments

def debug_print_code(locations):
    """
    Print the source lines from a list of locations on the debug stream.
    """
    locations_by_filename = defaultdict(list)
    for l in locations:
        locations_by_filename[l.filepath].append(l.lineno)
    for filepath, linenos in locations_by_filename.items():
        yield '', filepath
        filelines = Path(filepath).read_text().splitlines()
        for l in sorted(linenos):
            yield l, filelines[l-1]

def main():
    global args
    args = parse_args()

    target = Path(args.target[0])
    target_args = args.target[1:]
    dynamic_locations = args.pin.run(target, target_args)
    log.debug(f'{len(dynamic_locations)} logs')
    for l in dynamic_locations:
        log.debug(l)

    static_locations = get_static_locations(dynamic_locations)

    # Output trace locations to file
    all_locations = dynamic_locations + static_locations
    # log.debug(f'Removed {len(dynamic_locations) - len(unique_dynamic_locations)} duplicate dynamic locations')
    # log.debug(f'Removed {len(static_locations) - len(unique_static_locations)} duplicate static locations')
    # log.debug(f'Added {len(all_locations) - len(unique_dynamic_locations)} static locations to {len(unique_dynamic_locations)} dynamic locations totaling {len(all_locations)}')
    slim_locations = set(SlimLocation(l.filepath, l.lineno) for l in all_locations)
    
    if args.output_file:
        output_stream = open(args.output_file, 'w')
    else:
        output_stream = sys.stdout
    for l in slim_locations:
        output_stream.write(f'{l.filepath}:{l.lineno}\n')
    if output_stream is not sys.stdout:
        output_stream.close()

    for line, content in debug_print_code(slim_locations):
        log.debug(f'{line:4} {content}')

def get_static_locations(dynamic_locations):
    """
    Get locations for certain constructs which are only available statically.
    - Variable declarations without any executable code "int i;"
    - Case statements "case foo:"
    - Default statements "default: "
    """
    static_locations = []
    def ancestor_node(n):
        """
        Get the nearest significant ancestor.
        """
        if n.kind == CursorKind.FUNCTION_DECL:
            return n
        else:
            if n.semantic_parent is None:
                return n
            else:
                return ancestor_node(n.semantic_parent)
    
    def good(n):
        """
        Node should be added to the trace.
        """
        if n.kind in (CursorKind.VAR_DECL, CursorKind.CASE_STMT, CursorKind.DEFAULT_STMT):
            return True
        else:
            return False

    filepaths = defaultdict(list)
    for l in dynamic_locations:
        filepaths[l.filepath].append(l)
    for filepath, locations in filepaths.items():
        log.debug(f'Parsing source file {filepath}')
        root = nodeutils.parse(filepath)
        ancestors = []
        file = File.from_name(root.translation_unit, filepath)
        for l in locations:
            source_location = SourceLocation.from_position(root.translation_unit, file, l.lineno, l.column)
            node = Cursor.from_location(root.translation_unit, source_location)
            if node.kind.is_invalid():
                continue
            ancestor = ancestor_node(node)
            if ancestor not in ancestors:
                log.debug(f'node {nodeutils.pp(node)} has ancestor {nodeutils.pp(ancestor)}')
                ancestors.append(ancestor)
        for a in ancestors:
            if a.kind.is_translation_unit():
                continue # Do not include global constructs
            else:
                nodes = nodeutils.find(a, good)
                locations = [Location(n.location.file.name, n.location.line, n.location.column) for n in nodes]
                for l in locations:
                    log.debug(l)
                static_locations += locations

    return static_locations

if __name__ == '__main__':
    main()

