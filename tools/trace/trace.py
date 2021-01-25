#!/bin/python3

from mylog import log
import argparse
import logging
import nodeutils
from clang.cindex import CursorKind
from pathlib import Path
import subprocess
from collections import namedtuple

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs in -lDEBUG')
    parser.add_argument('-p', '--pin-root', help='Use an alternative path to Pin root.', default='pin-3.16')
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
    logs = pin.run(target)
    log.debug(f'{len(logs)} logs')
    for l in logs:
        log.debug(l)

    root = nodeutils.parse('test.c')
    vd = nodeutils.find(root, CursorKind.VAR_DECL) + nodeutils.find(root, CursorKind.CASE_STMT) + nodeutils.find(root, CursorKind.DEFAULT_STMT)
    for v in vd:
        log.debug(nodeutils.pp(v))

if __name__ == '__main__':
    main()

