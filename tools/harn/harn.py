#!/bin/python3

"""
Generate a test harness for a fault signature
"""

from clang.cindex import CursorKind, TypeKind

import argparse
import shutil
import subprocess
import os
import logging
import re

from mylog import log
from pathlib import Path
from nodeutils import find, parse, pp


def stmts_for_param(type, varname, stack=[]):
    """
    Yields input variables for type t's fields, down to primitives
    """

    type = type.get_canonical()

    decls = []
    inits = []
    shift_argv = 'shift_argi()'

    log.debug(f'variable {varname} type {type.spelling} (kind {type.kind})')

    if not (type.kind == TypeKind.FUNCTIONPROTO or (type.kind == TypeKind.POINTER and type.get_pointee().kind == TypeKind.FUNCTIONPROTO)):
        decls.append(f'{type.spelling} {varname.replace(".", "_")};')

    if type.kind == TypeKind.ELABORATED or type.kind == TypeKind.RECORD:
        td = type.get_declaration()
        children = list(td.get_children())
        inits.append(f'// assign fields for {varname}')
        if any(children):
            for child in children:
                child_varname = f'{varname}.{child.spelling}'
                if child.kind == CursorKind.UNION_DECL:
                    pass
                elif child.type.get_declaration().kind == CursorKind.UNION_DECL:
                    inits.append(f'// TODO union {child_varname} = <{", ".join(c.spelling for c in child.type.get_declaration().get_children())}>;')
                elif child.type.kind == TypeKind.POINTER:
                    if child.type.spelling in (s.spelling for s in stack) or child.type.get_pointee() == type:
                        inits.append(f'// TODO recursive {child_varname} = <{type.spelling}>;')
                    else:
                        if child.type.get_pointee().kind == TypeKind.CHAR_S:
                            inits.append(f'{child_varname} = {shift_argv};')
                        elif child.type.spelling in (s.spelling for s in stack):
                            pass
                        else:
                            valname = f'{child.spelling.replace(".", "_")}_v'
                            yield from stmts_for_param(child.type.get_pointee(), valname, stack=stack+[child.type])
                            inits.append(f'{child_varname} = &{valname};')
                else:
                    child_inits = zip(*stmts_for_param(child.type, f'{child_varname}', stack=stack+[child.type]))
                    yield from (([], c) for l in child_inits for c in l)
        else:
            log.warning(f'no fields found for type {type.spelling} (kind {type.kind})')
    elif type.kind == TypeKind.POINTER:
        if type.get_pointee().kind == TypeKind.CHAR_S:
            inits.append(f'{varname} = {shift_argv};')
        elif type.get_pointee().kind == TypeKind.FUNCTIONPROTO:
            inits.append(f'// TODO functionptr {varname} = <{type.spelling}>;')
        else:
            valname = f'{varname}_v'
            yield from stmts_for_param(type.get_pointee(), valname, stack=stack+[type])
            if type.get_pointee().kind != TypeKind.FUNCTIONPROTO:
                inits.append(f'{varname} = &{valname};')
    elif type.kind == TypeKind.INT or \
        type.kind == TypeKind.SHORT or \
        type.kind == TypeKind.LONG or \
        type.kind == TypeKind.LONGLONG or \
        type.kind == TypeKind.INT128 or \
        type.kind == TypeKind.ENUM:
        inits.append(f'{varname} = atoi({shift_argv});')
    elif type.kind == TypeKind.UINT or \
        type.kind == TypeKind.ULONG or \
        type.kind == TypeKind.ULONGLONG or \
        type.kind == TypeKind.UINT128:
        inits.append(f'{varname} = strtoul({shift_argv}, NULL, 10);')
    elif type.kind == TypeKind.CHAR_S:
        inits.append(f'{varname} = {shift_argv}[0];')
    elif type.kind == TypeKind.FUNCTIONPROTO:
        pass
    else:
        inits.append(f'// TODO unhandled {varname} = <{type.spelling}>;')
    
    yield decls, inits


def stmtgen(parameters):
    """
    Get declaration and initializer statements for the given parameters
    """
    decls = []
    inits = []

    for i, parm in enumerate(parameters):
        stmts = list(stmts_for_param(parm.type, parm.displayname))
        parm_decls, parm_inits = zip(*stmts)
        log.info(
            f'parameter {pp(parm)}({i}) produces {len(parm_decls)} local variable declarations and {len(parm_inits)} initializer statements')
        for v, i in stmts:
            log.debug(f'local variable {v} has initializer(s) {i}')
        decls += (i for ilist in parm_decls for i in ilist)
        inits += (i for ilist in parm_inits for i in ilist)

    return decls, inits


def callgen(fn, parameters):
    """
    Generate a call to the function, with the given parameters
    """
    parameters_text = ', '.join(p.spelling for p in parameters)
    return f'{fn.spelling}({parameters_text});'


def codegen(target):
    """
    Generate code for parameter names and code statements
    """
    
    parameters = list(target.get_arguments())
    log.info(f'target function has {len(parameters)} parameters')

    decls, inits = stmtgen(parameters)
    call = callgen(target, parameters)

    template = '''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// argi is used for iterating through the input arguments
int argi = 1;
int global_argc;
char **global_argv;

char *shift_argi() {{
    int old_argi = argi;
    argi++;
    assert(old_argi < global_argc);
    char *return_value = global_argv[old_argi];
    if (strcmp(return_value, "NULL") == 0) {{
        return_value = NULL;
    }}
    return return_value;
}}

int main(int argc, char **argv) {{
global_argc = argc;
global_argv = argv;

// declarations
{declarations}

// initializers
{initializers}

// call into segment
{call}
}}
'''
    sub = template.format(declarations='\n'.join(decls), initializers='\n'.join(inits), call=call)
    return sub


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
        target = max(funcdecls, key=lambda n: n.location.line if n.spelling !=
                     'main' and n.location.file.name.endswith('.c') else -1)
    log.info(f'target function: {pp(target)}')
    return target


def get_clang_flags(args):
    """
    Aggregate clang flags from args and Makefile if specified
    """
    clang_flags = args.clang_flags[0].split() if args.clang_flags else []
    if args.directory:
        args.directory = Path(args.directory)
        makefile = args.directory/'Makefile'
        log.debug(f'path to Makefile: {makefile}')
        assert(makefile.is_file())
        clang_flags += [f'-I{args.directory.absolute()}']
        clang_flags += re.findall(r'-I[^\s]+', open(makefile, 'r').read())
    return clang_flags


def output(args, input_text, test_harness):
    """
    Output test_harness to file or stdout, depending on args
    """
    outfile = args.output[0] if args.output else None

    raw_text = f'''
{input_text}
// test harness
{test_harness}
'''

    if outfile:
        log.info(f'writing to output file {outfile}')
        with open(outfile, 'w') as f:
            f.write(raw_text)
        if not args.no_format:
            if shutil.which('clang-format'):
                subprocess.call(['clang-format', outfile, '-i', '-style=Google'])
            else:
                log.warn('clang-format not found')
    else:
        log.info('generated test harness:')
        if not args.no_format:
            if shutil.which('clang-format'):
                tmp_filename = '/tmp/parse.py.fmt.c'
                log.info(f'writing to temporary file {tmp_filename}')
                with open(tmp_filename, 'w') as f:
                    f.write(raw_text)
                subprocess.call(['clang-format', tmp_filename, '-i', '-style=Google'])
                with open(tmp_filename, 'r') as f:
                    formatted_text = f.read()
                os.remove(tmp_filename)
                print(formatted_text)
            else:
                log.warn('clang-format not found')
        else:
            print(raw_text)


def read_input_file(translation_unit):
    input_lines = open(translation_unit.spelling, 'r').readlines()
    def is_main_definition(n):
        return n.kind == CursorKind.FUNCTION_DECL and n.is_definition() and n.spelling == 'main'
    main_def = next(iter(find(translation_unit, is_main_definition)), None)
    if main_def:
        start, end = main_def.extent.start.line, main_def.extent.end.line
        input_lines = input_lines[:start-1] + input_lines[end:]
    return ''.join(input_lines)


def get_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('input_file', help="Path to the input file. Can be a full filepath or, if -d is specified a path relative to the project directory.")
    parser.add_argument(
        '-d', '--directory', help='Directory of input project', type=str)
    parser.add_argument(
        '-o', '--output', help='Path to the output file', type=str, nargs=1)
    parser.add_argument('-c', '--clang_flags',
                        help='Flags to pass to clang e.g. -I</path/to/include>', type=str, nargs=1)
    parser.add_argument(
        '-f', '--no-format', help='Don\'t format the output file with clang-format', action="store_true")
    parser.add_argument(
        '-n', '--func-name', help='Target a specific function (defaults to the last function in the input file)', type=str, nargs=1)
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (ex. DEBUG, INFO, ERROR)', type=str)

    return parser.parse_args()


def main():
    args = get_args()
    if args.log_level:
        log.setLevel(logging.getLevelName(args.log_level))
    else:
        log.setLevel(logging.ERROR)

    func_name = args.func_name[0] if args.func_name else None
    clang_flags = get_clang_flags(args)
    log.info(f'clang_flags={clang_flags}')

    try:
        infile = Path(args.input_file)
        if not infile.is_file():
            infile = Path(args.directory) / args.input_file
        assert(infile.is_file())
        log.info(f'infile={infile}')
        cur = parse(infile, args=clang_flags)

        target = select_target(func_name, cur)
        test_harness = codegen(target)
        input_text = read_input_file(cur)
        output(args, input_text, test_harness)
    except:
        log.exception(f'error generating test harness from {args.input_file}')
        exit(1)


if __name__ == "__main__":
    main()
