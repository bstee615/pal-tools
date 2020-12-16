#!/bin/python3

from mylog import log
import logging
import argparse
import pandas
import os
import re
import subprocess
import shutil
import difflib

'''
Parse Xueyuan's human readable assertions
'''

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

def parse(dirname, assertion):
    dirname = os.path.abspath(dirname)
    m = re.match(r'([^,]+),\s*(before|after)\s*line\s*([0-9]+).*(assert\(.*\);)', assertion)
    file_path = os.path.join(dirname, m.group(1))
    before_after = m.group(2)
    line_no = int(m.group(3))
    assert_stmt = m.group(4)
    assert_args = re.match(r'assert\((.*)\);', assert_stmt).group(1)
    my_assert_stmt = f'if (!{assert_args}) {{*((int*)0) = 0;}} // my_assert'
    my_assert_stmt += '\n'

    log.debug(f'{file_path}:{line_no} {my_assert_stmt}')

    fromlines = open(file_path, 'r').readlines()
    if before_after == 'before':
        tolines = fromlines[:line_no-1] + [my_assert_stmt] + fromlines[line_no-1:]
    elif before_after == 'after':
        tolines = fromlines[:line_no] + [my_assert_stmt] + fromlines[line_no:]
    else:
        log.critical(f'before_after is not valid: {before_after}')
        return

    unidiff = difflib.unified_diff(fromlines, tolines, fromfile=file_path, tofile=file_path)
    patch = ''.join(unidiff)
    # log.debug(patch)
    return patch

def main():
    df = pandas.read_csv('notes.tsv', sep='\t')

    for i, row in df.iterrows():
        name = row['Name']
        bug = row['Bug']
        buggy_version = bug.split('-')[-2]
        assertion = row['Assert']

        dirname = os.path.join('functional', bug)

        # Copy to buggy folder
        buggy_dirname = os.path.join(dirname, f'buggy.{buggy_version}')
        if not os.path.isdir(buggy_dirname):
            src_dirname = os.path.join(dirname, name)
            try:
                print('copying', src_dirname, 'to', buggy_dirname)
                shutil.copytree(src_dirname, buggy_dirname)
            except:
                print('error, trying cp -r')
                subprocess.check_call(args=['cp', '-r', src_dirname, buggy_dirname])

        patch = parse(buggy_dirname, assertion)
        assert_file = os.path.join(buggy_dirname, 'my_assert.patch')
        log.debug(f'writing patch to {assert_file}')
        open(assert_file, 'w').write(patch)

if __name__ == '__main__':
    main()
