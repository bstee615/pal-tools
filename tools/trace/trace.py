#!/bin/python3

from mylog import log
import argparse
import logging
import nodeutils
from clang.cindex import CursorKind
from pathlib import Path
import subprocess
from collections import namedtuple
import itertools

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    parser.add_argument('-p', '--pin-root', type=str, help='Use an alternative path to Pin root.', default='pin-3.16')
    parser.add_argument('-o', '--output-file', type=str, help='Output to a file')
    arguments = parser.parse_args()
    
    if arguments.log_level:
        log.setLevel(logging.getLevelName(arguments.log_level))
    
    if arguments.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    arguments.pin_root = Path(__file__).parent / arguments.pin_root

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
        lineno = line[split_index+1:]
        locations.append(Location(filepath, lineno))
    return locations

class Pin:
    def __init__(self, pin_root):
        self.root = Path(pin_root)
    
    def run(self, target):
        """
        Run Pin. Collect results in temporary file pin.log
        and return a list of trace locations (filepath:lineno).
        """
        if not target.is_file():
            log.warn(f'No such file for target executable: {target}')
            return []

        exe = self.root / 'pin'
        lib = self.root / 'source/tools/trace-pintool/obj-intel64/trace.so'
        if not exe.is_file():
            log.warn(f'No such file for Pin executable: {exe}')
            return []
        if not lib.is_file():
            log.warn(f'No such file for trace-pintool: {lib}')
            return []

        logfile = Path('pin.log')
        cmd = f'{exe} -t {lib} -o {logfile} -- {target.absolute()}'
        args = cmd.split()
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = p.communicate()
        return_code = p.returncode
        log.debug(f'Ran "{cmd}" with return code {return_code}')

        if return_code != 0:
            log.warn(f'Error {return_code} running pin with command: "{cmd}"')
            log.warn(f'Echoing stderr:')
            log.warn(err.decode())
            log.warn(f'Echoing stdout:')
            log.warn(err.decode())
            return []
        
        if not logfile.is_file():
            log.warn(f'Something went wrong logging to {logfile}.')
            return []
        
        return parse_pinlog(logfile)

def main():
    pin = Pin(args.pin_root)
    target = Path('test')
    dynamic_locations = pin.run(target)
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

    if args.output_file:
        with open(args.output_file) as f:
            for l in dynamic_locations + static_locations:
                f.write(f'{l.filepath}:{l.lineno}\n')
    else:
        for l in dynamic_locations + static_locations:
            print(f'{l.filepath}:{l.lineno}')

if __name__ == '__main__':
    main()

