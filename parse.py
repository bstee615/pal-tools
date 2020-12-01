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
import sys

log = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
verbose_fmt = logging.Formatter('%(levelname)s - %(message)s')
stdout_handler.setFormatter(verbose_fmt)
log.addHandler(stdout_handler)

def pp(node):
    """
    Return str of node for pretty print
    """
    return f'{node.displayname} ({node.kind}) [{node.location}]'

def find(node, kind):
    """
    Return all node's descendants of a certain kind
    """

    log.debug(f'find: walked node {pp(node)}')

    if node.kind == kind:
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find(child, kind)

from dataclasses import dataclass
from typing import Any
@dataclass
class LocalVariable:
    type: Any = None
    name: Any = None
    children: Any = 0

def local_vars(type, varname):
    """
    Yields input variables for type t's fields, down to primitives
    """

    if type.kind == TypeKind.ELABORATED:
        td = type.get_declaration()
        children = list(td.get_children())
        # TODO: Test for missing struct declaration
        for fd in children:
            yield from local_vars(fd.type, fd.displayname)
        yield LocalVariable(type, varname, len(children))
    elif type.kind == TypeKind.POINTER:
        if type.spelling == 'char *':
            yield LocalVariable(type, varname, 0)
        else:
            # TODO: Currently inits all ptrs as single values. What about arrays?
            yield from local_vars(type.get_pointee(), f'{varname}_v')
            yield LocalVariable(type, varname, 1)
    elif type.kind == TypeKind.INT:
        yield LocalVariable(type, varname)
    elif type.kind == TypeKind.UINT:
        yield LocalVariable(type, varname)
    elif type.kind == TypeKind.CHAR_S:
        yield LocalVariable(type, varname)
    else:
        raise Exception('local variables unhandled kind', type.kind)

def initializers(vars):
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

// BEGIN cleanup input variables
{cleanups}
// END cleanup input variables

// BEGIN call into segment
{fn_name}({", ".join(param_names)});
// END call into segment
}}
// END test harness
'''

def generate_harness(infile):
    """
    Generate and return a test harness, a chunk of C code that defines a main method
    to initialize input variables and call the target function
    """

    index = clang.cindex.Index.create()
    tu = index.parse(infile)
    log.info(f'translation unit: {tu.spelling}')
    
    cur = tu.cursor

    funcdecls = find(cur, CursorKind.FUNCTION_DECL)
    target = max(funcdecls, key=lambda n: n.location.line if n.spelling != 'main' and n.location.file.name == infile else -1)
    log.info(f'target function: {pp(target)}')

    inits = []
    parmesan = list(find(target, CursorKind.PARM_DECL))
    log.info(f'target function has {len(parmesan)} parameters')
    for i, parm in enumerate(parmesan):
        locals = list(local_vars(parm.type, parm.displayname))
        this_boy_inits = list(initializers(locals))
        inits += this_boy_inits
        log.info(f'parameter {i} {pp(parm)} produces {len(locals)} local variables')
        for l in locals:
            log.debug(f'local variable {l}')

    param_names = (p.displayname for p in parmesan)
    return codegen(target.spelling, param_names, inits)

def get_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('input_file', help="Path to the input file")
    parser.add_argument('-o', "--output", help="Path to the output file", type=str, nargs=1)
    parser.add_argument('-f', "--format", help="Format the output file with clang-format", action="store_true")
    parser.add_argument('-l', "--logs", help="Print informational logs to stdout", action="store_true")
    parser.add_argument('-v', "--verbose", help="Print informational and diagnostic logs to stdout", action="store_true")

    return parser.parse_args()

def main():
    args = get_args()
    outfile = args.output[0] if args.output else None
    log.setLevel(logging.DEBUG)
    if args.logs:
        stdout_handler.setLevel(logging.INFO)
    elif args.verbose:
        stdout_handler.setLevel(logging.DEBUG)
    else:
        stdout_handler.setLevel(logging.CRITICAL)

    test_harness = ""
    try:
        test_harness =  generate_harness(args.input_file)
    except:
        log.exception(f'error generating test harness from {args.input_file}')
        exit(1)

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
