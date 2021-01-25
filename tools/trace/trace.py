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

def parse_args():
    file_dir = Path(__file__).parent
    default_pinroot = str(file_dir / 'pin-3.16')

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
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

    if not arguments.pin_root.is_dir():
        log.warn(f'{arguments.pin_root} is not a valid Pin installation. See {file_dir}/install.sh for the recommended method for installing Pin.')
        exit(1)

    return arguments

args = parse_args()
verbose=False

Location = namedtuple('Location', 'filepath lineno')

def parse_pinlog(logfile):
    """
    Parse a Pin log file and return the trace locations.
    """
    logtext = logfile.read_text()
    loglines = logtext.splitlines()
    locations = []
    for line in loglines:
        split_index = line.rindex(':')
        filepath = line[:split_index]
        lineno = int(line[split_index+1:])
        locations.append(Location(filepath, lineno))
    return locations

class Pin:
    def __init__(self, pin_root):
        self.root = Path(pin_root)
    
    def run(self, target, target_args):
        """
        Run Pin. Collect results in temporary file pin.log
        and return a list of trace locations (filepath:lineno).
        """
        if not target.is_file():
            log.error(f'No such file for target executable: {target}')
            return []

        exe = self.root / 'pin'
        lib = self.root / 'source/tools/trace-pintool/obj-intel64/trace.so'
        if not exe.is_file():
            log.error(f'No such file for Pin executable: {exe}')
            return []
        if not lib.is_file():
            log.error(f'No such file for trace-pintool: {lib}')
            return []

        logfile = Path('pin.log')
        cmd = f'{exe} -t {lib} -o {logfile} -- {target.absolute()}'
        args = cmd.split() + target_args
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = p.communicate()
        return_code = p.returncode
        log.debug(f'Ran "{cmd}" with return code {return_code}')

        # Pin tool exits 1 on success ¯\_(ツ)_/¯
        if return_code != 1:
            log.warn(f'Got {return_code} running pin with command: "{cmd}"')
            log.warn(f'Echoing stderr:')
            log.warn(err.decode())
            log.warn(f'Echoing stdout:')
            log.warn(output.decode())
        
        if not logfile.is_file():
            log.error(f'Something went wrong logging to {logfile}.')
            return []
        
        return parse_pinlog(logfile)

def log_code(locations):
    locations_by_filename = defaultdict(list)
    for l in locations:
        locations_by_filename[l.filepath].append(l.lineno)
    for filepath, linenos in locations_by_filename.items():
        log.debug(filepath)
        filelines = Path(filepath).read_text().splitlines()
        for l in sorted(linenos):
            log.debug(f'{l:4} {filelines[l-1]}')

def main():
    pin = Pin(args.pin_root)
    target = Path(args.target[0])
    target_args = args.target[1:]
    dynamic_locations = pin.run(target, target_args)
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
    all_locations = set(dynamic_locations + static_locations)
    if args.output_file:
        output_stream = open(args.output_file, 'w')
    else:
        output_stream = sys.stdout
    for l in all_locations:
        output_stream.write(f'{l.filepath}:{l.lineno}\n')
    if output_stream is not sys.stdout:
        output_stream.close()

    log_code(all_locations)

if __name__ == '__main__':
    main()

