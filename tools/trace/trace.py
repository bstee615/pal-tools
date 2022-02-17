#!/bin/python3

from mylog import log
import argparse
import logging
import nodeutils
from clang.cindex import Config, Cursor, CursorKind, File, SourceLocation
from pathlib import Path
from collections import defaultdict
import sys
from .pin import Pin
from .location import Location, SlimLocation
import traceback

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
    parser.add_argument('-k', '--keep-logfile', action='store_true', help='Keep the log file after running Pin')
    parser.add_argument('-s', '--include_static', action='store_true', help='Output static trace')
    parser.add_argument('--include_code', action='store_true', help='Output code statements')
    parser.add_argument('--include_column', action='store_true', help='Output column numbers')
    parser.add_argument('-p', '--pin-root', type=str, help=f'Use an alternative path to Pin root. Default: {default_pinroot}', default=default_pinroot)
    parser.add_argument('-o', '--output-file', type=str, help='Output to a file')
    parser.add_argument('-I', default=[], dest='clang_include_paths', action='append', help='Include paths to pass to Clang (same as clang\'s -I flag)')
    parser.add_argument('--clang_library_file', type=str, help='Library file to load for Libclang stuff')
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
        arguments.pin = Pin.do_wizard(arguments, file_dir / 'install.sh')
    else:
        arguments.pin = Pin(arguments)

    if arguments.clang_library_file:
        log.debug(f'Setting clang library file to {arguments.clang_library_file}')
        Config.set_library_file(arguments.clang_library_file)

    log.debug(f'arguments: {arguments}')

    return arguments

def debug_print_code(locations):
    """
    Print the source lines from a list of locations on the debug stream.
    """
    linenos_by_filepath = defaultdict(list)
    linetext_by_filepath = defaultdict(list)
    for l in locations:
        linenos_by_filepath[l.filepath].append(l.lineno)
    for f in linenos_by_filepath:
        linenos_by_filepath[f] = sorted(linenos_by_filepath[f])
    for filepath, linenos in linenos_by_filepath.items():
        filelines = Path(filepath).read_text().splitlines()
        for l in sorted(linenos):
            linetext_by_filepath[filepath].append(filelines[l-1])
    return {fp:list(zip(linenos_by_filepath[fp], linetext_by_filepath[fp])) for fp in linenos_by_filepath}

def get_code(node):
    if node.kind in (CursorKind.IF_STMT, CursorKind.FOR_STMT, CursorKind.WHILE_STMT, CursorKind.DO_STMT, CursorKind.SWITCH_STMT):
        node = [c for c in node.get_children()][0]
    return ' '.join(t.spelling for t in node.get_tokens())

def slim(locations, add_code):
    """Store only filepath and lineno and dedup"""
    slim_locations = []
    for l in locations:
        if add_code:
            sl = SlimLocation(l.filepath, l.lineno, l.column, get_code(l.node))
        else:
            sl = SlimLocation(l.filepath, l.lineno, l.column, None)
        if len(slim_locations) == 0 or slim_locations[-1] != sl:
            slim_locations.append(sl)
    return slim_locations


def main():
    global args
    args = parse_args()

    target = Path(args.target[0])
    target_args = args.target[1:]
    try:
        dynamic_locations = args.pin.run(target, target_args)
    except Exception as e:
        log.error(e)
        log.error(traceback.format_exc())
        return -1
    log.debug(f'{len(dynamic_locations)} logs')
    
    for l in dynamic_locations:
        if Path(l.filepath).exists():
            log.debug(f'dynamic location {l}')
        elif args.verbose:
            log.debug(f'dynamic location {l}')
            log.debug(f'^^^ file does not exist ^^^')
    
    dynamic_locations = [d for d in dynamic_locations if Path(d.filepath).exists()]

    static_locations = []
    clang_include_paths = [f'-I{p}' for p in args.clang_include_paths]
    static_locations = get_static_locations(dynamic_locations, clang_include_paths)

    # Store only filepath and lineno and dedup
    all_locations = slim(dynamic_locations, args.include_code)
    if args.include_static:
        all_locations += slim(static_locations, args.include_code)
    
    # Output trace locations to file
    if args.output_file:
        output_stream = open(args.output_file, 'w')
    else:
        output_stream = sys.stdout
    for l in all_locations:
        s = f'{l.filepath}:{l.lineno}'
        if args.include_column:
            s += f':{l.column}'
        if args.include_code:
            s += f':{l.code}'
        s += '\n'
        output_stream.write(s)
    if output_stream is not sys.stdout:
        output_stream.close()

    debug_info = debug_print_code(all_locations)
    for filepath, content in debug_info.items():
        log.debug(filepath)
        for lineno, text in content:
            log.debug(f'{lineno:4} {text}')
    return 0

def get_static_locations(dynamic_locations, clang_include_paths):
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
        log.debug(f'Parsing source file {filepath} with args {clang_include_paths}')
        root = nodeutils.parse(filepath, clang_include_paths)
        ancestors = []
        file = File.from_name(root.translation_unit, filepath)
        for l in locations:
            source_location = SourceLocation.from_position(root.translation_unit, file, l.lineno, l.column)
            node = Cursor.from_location(root.translation_unit, source_location)
            l.node = node
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
                locations = [Location(n.location.file.name, n.location.line, n.location.column, n) for n in nodes]
                for l in locations:
                    log.debug(f'static location {l}')
                static_locations += locations

    return static_locations

if __name__ == '__main__':
    exit(main())

