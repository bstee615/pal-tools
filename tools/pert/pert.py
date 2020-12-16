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
    parser.add_argument('filter', nargs='?', help='Filter bugs to a certain filter')
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

def parse(dirname, buggy_dirname, assertion):
    dirname = os.path.abspath(dirname)
    m = re.match(r'([^,]+),\s*(before|after)\s*line\s*([0-9]+)\s*\((.*)\),\s*(assert\(.*\);)', assertion)
    file_path = os.path.join(dirname, m.group(1))
    buggy_file_path = os.path.join(dirname, m.group(1))
    before_after = m.group(2)
    line_no = int(m.group(3))
    expr = m.group(4).strip()
    assert_stmt = m.group(5)
    assert_args = re.match(r'assert\((.*)\);', assert_stmt).group(1)
    my_assert_stmt = f'if (!{assert_args}) {{*((int*)0) = 0;}} // my_assert'
    my_assert_stmt += '\n'
    
    log.info(f'{before_after} {file_path}:{line_no} "{my_assert_stmt}"')

    fromlines = open(file_path, 'r').readlines()
    
    matchto = [l.strip() for l in [fromlines[line_no-(2 if before_after == 'begin' else 1)]]]
    matches = difflib.get_close_matches(expr, matchto)
    log.debug(f'close matching "{expr}"')
    assert(len(matches) > 0)
    log.debug(f'close matched {file_path}:{line_no} "{fromlines[line_no-1]}"')

    if before_after == 'before':
        tolines = fromlines[:line_no-1] + [my_assert_stmt] + fromlines[line_no-1:]
    elif before_after == 'after':
        tolines = fromlines[:line_no] + [my_assert_stmt] + fromlines[line_no:]
    else:
        log.critical(f'before_after is not valid: {before_after}')
        return

    unidiff = difflib.unified_diff(fromlines, tolines, fromfile=buggy_file_path, tofile=buggy_file_path)
    patch = ''.join(unidiff)
    return patch

def main():
    df = pandas.read_csv('notes.tsv', sep='\t')
    filtered = []
    if args.filter:
        for name_regex in args.filter.split(','):
            name_regex = f'^{name_regex}'
            filtered.append(df.loc[df['Bug'].str.contains(name_regex), :])
        df = pandas.concat(filtered)

    for i, row in df.iterrows():
        name = row['Name']
        bug = row['Bug']
        buggy_version = bug.split('-')[-2]
        assertion = row['Assert']

        dirname = os.path.join('functional', bug)

        # Copy to buggy folder
        src_dirname = os.path.join(dirname, name)
        buggy_dirname = os.path.join(dirname, f'buggy.{buggy_version}')
        if not os.path.isdir(buggy_dirname):
            try:
                print('copying', src_dirname, 'to', buggy_dirname)
                shutil.copytree(src_dirname, buggy_dirname)
            except:
                print('error, trying cp -r')
                subprocess.check_call(args=['cp', '-r', src_dirname, buggy_dirname])

        patch = parse(src_dirname, buggy_dirname, assertion)
        assert_file = os.path.join(buggy_dirname, 'my_assert.patch')
        log.info(f'generated patch {assert_file}')
        open(assert_file, 'w').write(patch)

if __name__ == '__main__':
    main()
