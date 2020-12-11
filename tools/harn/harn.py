#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex
from clang.cindex import CursorKind, TypeKind

import argparse
import shutil
import subprocess
import os
import logging
import re

from mylog import log
from nodeutils import find, parse, pp

from dataclasses import dataclass
from typing import Any

@dataclass
class LocalVariable:
    type: Any = None
    name: Any = None
    children: Any = 0

def locals_for_param(type, varname):
    """
    Yields input variables for type t's fields, down to primitives
    """

    if type.kind == TypeKind.ELABORATED:
        td = type.get_declaration()
        children = list(td.get_children())
        # TODO: Test for missing struct declaration
        for fd in children:
            yield from locals_for_param(fd.type, fd.displayname)
        yield LocalVariable(type, varname, len(children))
    elif type.kind == TypeKind.POINTER:
        if type.spelling == 'char *':
            yield LocalVariable(type, varname, 0)
        else:
            # TODO: Currently inits all ptrs as single values. What about arrays?
            yield from locals_for_param(type.get_pointee(), f'{varname}_v')
            yield LocalVariable(type, varname, 1)
    elif type.kind == TypeKind.INT:
        yield LocalVariable(type, varname)
    elif type.kind == TypeKind.UINT:
        yield LocalVariable(type, varname)
    elif type.kind == TypeKind.CHAR_S:
        yield LocalVariable(type, varname)
    else:
        raise Exception('local variables unhandled kind', type.kind)

def initializers_for_locals(vars):
    """
    Yields C statements to declare and read values for input vars.
    """
    
    def declare(v):
        return f'{v.type.spelling} {v.name};'
        
    def throwaway_getline(var_name, fmt):
        """
        Declare a string and string length variable, call getline, assign result then free the buffer
        """

        str_name = f'{var_name}_s'
        strlen_name = f'{var_name}_sn'
        return f'''// BEGIN read value for {var_name}
char *{str_name}=NULL;
size_t {strlen_name}=0;
printf("{var_name}: ");
getline(&{str_name}, &{strlen_name}, stdin);
{fmt.format(var_name, str_name, strlen_name)} // provided line
free({str_name});
// END read value for {var_name}'''

    def read_and_assign(i, v):
        vars_so_far = vars[:i]
        if v.type.kind == TypeKind.ELABORATED:
            assignments = '\n'.join(f'{v.name}.{c.name} = {c.name};' for c in reversed(vars_so_far[-v.children:]))
            return f'''// BEGIN assign fields of {v.name}
{assignments}
// END assign fields of {v.name}'''
        elif v.type.kind == TypeKind.POINTER:
            if v.type.spelling == 'char *':
                return throwaway_getline(v.name, '{0} = malloc({2});\nstrcpy({0}, {1});')
            else:
                # TODO: Currently inits all ptrs as single values. What about arrays?
                return f'''// BEGIN assign ptr {v.name}
{v.name} = &{vars_so_far[-v.children].name};
// END assign ptr {v.name}'''
        elif v.type.kind == TypeKind.INT:
            return throwaway_getline(v.name, '{0} = atoi({1});')
        elif v.type.kind == TypeKind.UINT:
            return throwaway_getline(v.name, '{0} = strtoul({1}, NULL, 10);')
        elif v.type.kind == TypeKind.CHAR_S:
            return throwaway_getline(v.name, '{0} = {1}[0];')
        else:
            raise Exception('definitions unhandled kind', type.kind)

    def cleanup(v):
        if v.type.kind == TypeKind.POINTER and v.type.spelling == 'char *':
            return f'free({v.name});'

    for i, v in enumerate(vars):
        yield (declare(v), read_and_assign(i, v), cleanup(v))

def codegen(fn_name, param_names, inits):
    decls, defs, cleanups = ('\n'.join(filter(lambda x: x, l)) for l in zip(*inits))

    return f'''
// BEGIN test harness
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {{
// BEGIN declare input variables
{decls}
// END declare input variables

// BEGIN read input variables
{defs}
// END read input variables

// BEGIN call into segment
{fn_name}({", ".join(param_names)});
// END call into segment

// BEGIN cleanup input variables
{cleanups}
// END cleanup input variables
}}
// END test harness
'''

def get_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('input_file', help="Path to the input file")
    parser.add_argument('-o', '--output', help='Path to the output file', type=str, nargs=1)
    parser.add_argument('-c', '--clang_flags', help='Flags to pass to clang e.g. -I</path/to/include>', type=str, nargs=1)
    parser.add_argument('-m', '--makefile', help='Path to Makefile containing flags to pass to clang in CFLAGS variable e.g. CFLAGS:=-I</path/to/include>', type=str, nargs=1)
    
    parser.add_argument('-f', '--format', help='Format the output file with clang-format', action="store_true")
    parser.add_argument('-n', '--func-name', help='Target a specific function (defaults to the last function in the input file)', type=str, nargs=1)
    parser.add_argument('-l', '--logs', help='Print informational logs to stdout', action="store_true")
    parser.add_argument('-v', '--verbose', help='Print informational and diagnostic logs to stdout', action="store_true")

    return parser.parse_args()

def main():
    args = get_args()
    if args.logs:
        log.setLevel(logging.INFO)
    elif args.verbose:
        log.setLevel(logging.DEBUG)

    func_name = args.func_name[0] if args.func_name else None
    clang_flags = get_clang_flags(args)

    try:
        infile = args.input_file
        log.info(f'{clang_flags=}')

        cur = parse(infile, args=clang_flags)

        target = select_target(func_name, cur)

        parmesan = list(find(target, CursorKind.PARM_DECL))
        log.info(f'target function has {len(parmesan)} parameters')
        inits = get_initializers(parmesan)

        param_names = (p.displayname for p in parmesan)
        test_harness = codegen(target.spelling, param_names, inits)
        output(args, test_harness)
    except:
        log.exception(f'error generating test harness from {args.input_file}')
        exit(1)

def get_clang_flags(args):
    clang_flags = args.clang_flags[0].split() if args.clang_flags else []
    makefile = args.makefile[0] if args.makefile else None
    if makefile:
        with open(makefile, 'r') as f:
            for line in f.readlines():
                if m := re.search(r'CFLAGS:=(.*)', line):
                    clang_flags += m.group(1).split()
    return clang_flags

def get_initializers(parameters):
    """
    Get initializer statements for the given parameters
    """
    initializers = []
    for i, parm in enumerate(parameters):
        locals = list(locals_for_param(parm.type, parm.displayname))
        this_boy_inits = list(initializers_for_locals(locals))
        initializers += this_boy_inits
        log.info(f'parameter {i} {pp(parm)} produces {len(locals)} local variables')
        for l in locals:
            log.debug(f'local variable {l}')
    return initializers

def select_target(func_name, cur):
    """
    Select target function with the given name from cur
    """
    funcdecls = find(cur, CursorKind.FUNCTION_DECL)
    if func_name:
        target = next((n for n in funcdecls if n.spelling == func_name), None)
        if target is None:
            raise Exception(f'no function named {func_name}')
    else:
        target = max(funcdecls, key=lambda n: n.location.line if n.spelling != 'main' and n.location.file.name.endswith('.c') else -1)
    log.info(f'target function: {pp(target)}')
    return target

def output(args, test_harness):
    outfile = args.output[0] if args.output else None

    with open(args.input_file, 'r') as f:
        input_text = f.read()
    if '// BEGIN test harness' in input_text:
        log.critical('Test harness exists in the input file; please delete it')
        exit(1)
    raw_text = f'''//BEGIN original file
{input_text}
//END original file
{test_harness}
'''

    if outfile:
        log.info(f'writing to output file {outfile}')
        with open(outfile, 'w') as f:
            f.write(raw_text)
        if args.format:
            if shutil.which('clang-format'):
                subprocess.check_call(['clang-format', outfile, '-i'])
            else:
                log.warn('requested format but clang-format not found')
    else:
        log.info('generated test harness:')
        if args.format:
            if shutil.which('clang-format'):
                tmp_filename = '/tmp/parse.py.fmt.c'
                with open(tmp_filename, 'w') as f:
                    f.write(raw_text)
                subprocess.check_call(['clang-format', tmp_filename, '-i'])
                with open(tmp_filename, 'r') as f:
                    formatted_text = f.read()
                os.remove(tmp_filename)
                print(formatted_text)
            else:
                log.info('requested format but clang-format not found')
        else:
            print(raw_text)

if __name__ == "__main__":
    main()
