#!/bin/python3

from mylog import log
import logging
import argparse
import pandas
import os
import re
import subprocess
import shutil

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
    line_no = m.group(3)
    assert_stmt = m.group(4)
    assert_args = re.match(r'assert\((.*)\);', assert_stmt).group(1)
    my_assert_stmt = f'if (!{assert_args}) {{*((int*)0) = 0;}} // my_assert'

    print(before_after, f'{file_path}:{line_no}')
    print()
    print(my_assert_stmt)
    print()

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

        parse(buggy_dirname, assertion)

if __name__ == '__main__':
    main()
