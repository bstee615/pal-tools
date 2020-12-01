#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex
from clang.cindex import CursorKind, TypeKind

import argparse
import shutil
import subprocess
import os

def pp(node):
    """
    Return str of node for pretty print
    """
    return f'{node.displayname} ({node.kind}) [{node.location}]'

def find(node, kind, verbose=False):
    """
    Return all node's descendants of a certain kind
    """

    if verbose:
        print(pp(node))

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
        return f'''
// BEGIN read value for {var_name}
{{
char *{str_name}=NULL;
size_t {strlen_name}=0;
printf("{var_name}: ");
getline(&{str_name}, &{strlen_name}, stdin);
{fmt.format(var_name, str_name, strlen_name)} // provided line
free({str_name});
}}
// END read value for {var_name}
'''

    def read_and_assign(i, v):
        vars_so_far = vars[:i]
        if v.type.kind == TypeKind.ELABORATED:
            assignments = '\n'.join(f'{v.name}.{c.name} = {c.name};' for c in reversed(vars_so_far[-v.children:]))
            return f'''
// BEGIN assign fields of {v.name}
{assignments}
// END assign fields of {v.name}
'''
        elif v.type.kind == TypeKind.POINTER:
            if v.type.spelling == 'char *':
                return throwaway_getline(v.name, '{0} = malloc({2});\nstrcpy({0}, {1});')
            else:
                # TODO: Currently inits all ptrs as single values. What about arrays?
                return f'{v.name} = &{vars_so_far[-v.children].name};'
        elif v.type.kind == TypeKind.INT:
            return throwaway_getline(v.name, '{0} = atoi({1});')
        elif v.type.kind == TypeKind.UINT:
            return throwaway_getline(v.name, '{0} = strtoul({1}, NULL, 10);')
        elif v.type.kind == TypeKind.CHAR_S:
            return throwaway_getline(v.name, '{0} = {1}[0];')
        else:
            raise Exception('definitions unhandled kind', type.kind)

    for i, v in enumerate(vars):
        yield (declare(v), read_and_assign(i, v))

def codegen(fn_name, param_names, inits):
    decls, defs = zip(*inits)
    joiner = '\n'

    return f'''
// BEGIN test harness
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {{
// BEGIN declare input variables
{joiner.join(decls)}
// END declare input variables

// BEGIN read input variables
{joiner.join(defs)}
// END read input variables

// BEGIN call into segment
{fn_name}({", ".join(param_names)});
// END call into segment
}}
// END test harness
'''

def get_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('filename', help="Path to the input file")
    parser.add_argument('-o', "--output", help="Path to the output file", type=str, nargs=1)
    parser.add_argument('-f', "--format", help="Format the output file with clang-format", action="store_true")

    return parser.parse_args()

def main():
    args = get_args()
    infile = args.filename
    outfile = args.output[0] if args.output else None
    should_format = args.format

    index = clang.cindex.Index.create()
    tu = index.parse(infile)
    print('translation unit:', tu.spelling)
    
    cur = tu.cursor

    funcdecls = find(cur, CursorKind.FUNCTION_DECL)
    target = max(funcdecls, key=lambda n: n.location.line if n.spelling != 'main' and n.location.file.name == infile else -1)
    print(f'target function: {pp(target)}')

    inits = []
    parmesan = list(find(target, CursorKind.PARM_DECL))
    print(f'target function has {len(parmesan)} parameters')
    for i, parm in enumerate(parmesan):
        locals = list(local_vars(parm.type, parm.displayname))
        this_boy_inits = list(initializers(locals))
        inits += this_boy_inits
        print(f'parameter {i} {pp(parm)} produces {len(locals)} local variables')
        for l in locals:
            print(f'local variable {l}')

    param_names = (p.displayname for p in parmesan)
    test_harness = codegen(target.spelling, param_names, inits)

    with open(infile, 'r') as f:
        text = f.read()
    raw_text = text + '\n' + test_harness

    if outfile:
        with open(outfile, 'w') as f:
            f.write(raw_text)
        
        if should_format:
            if shutil.which('clang-format'):
                subprocess.check_call(['clang-format', outfile, '-i'])
            else:
                print('WARNING: Requested format but clang-format not found')
    else:
        print('generated test harness:')
        if should_format:
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
                print('WARNING: Requested format but clang-format not found')
        else:
            print(raw_text)

if __name__ == "__main__":
    main()
