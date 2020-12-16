from nodeutils import find, parse, pp
from clang.cindex import CursorKind, TypeKind

from mylog import log
import logging
import difflib
import argparse

verbose = False

def main():
    log.setLevel(logging.INFO)

    args = parse_args()

    if args.log_level:
        log.setLevel(args.log_level)
        log.debug(f'setting log level to {args.log_level}')

    seg_c = args.segment_file
    orig_dir = args.original_file
    log.debug(f'segment: {seg_c}, original: {orig_dir}')

    clang_args = args.clang_args.split()
    if clang_args:
        log.debug(f' provided clang args: {clang_args}')

    if args.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    seg_cur = parse(seg_c, clang_args)
    seg_target = select_target(seg_cur, target_name=args.target)
    parms = list(seg_target.get_arguments())

    log.debug(f'target: {pp(seg_target)}')
    import re
    target_name = re.match(r'helium_(.*)', seg_target.spelling).group(1)
    
    from pathlib import Path
    for orig_c in Path(orig_dir).glob('**/*.c'):
        orig_cur = parse(orig_c)
        orig_funcdecls = find(orig_cur, CursorKind.FUNCTION_DECL, verbose)
        orig_target = next((f.get_definition() for f in orig_funcdecls if is_the_same(f, seg_target) and f.get_definition() is not None), None)
        if orig_target is not None:
            break
    log.debug(f'target: {pp(orig_target)}')
    orig_body = find(orig_target, lambda c: c is not None and c.kind.is_statement(), verbose=verbose)
    first_stmt = next(iter(orig_body))
    first_stmt_file, first_stmt_line = first_stmt.location.file.name, first_stmt.location.line

    diff = gen_patch(first_stmt_file, first_stmt_line, parms, args.array)
    print('\n'.join(diff))

def gen_patch(file, line, parms, array_expressions):
    stmts = []

    stmts.append(f'b {file.split("/")[-1]}:{line}')

    arrays = dict(a.split(':') for a in array_expressions)
    log.debug(f'{len(parms)} parameters')
    printfs = list(gen_printfs(parms, arrays))
    log.debug(printfs)
    stmts += printfs

    return stmts

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('segment_file')
    parser.add_argument('original_file')
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs. Should be used in tandem with "-l DEBUG"')
    parser.add_argument('-a', '--array', action='append', default=[], help='Assign length expressions for array variables. Length expressions are in the format "array:length", where array is the name of the array and length is a C expression to be evaluated at runtime, typically a number or variable reference')
    parser.add_argument('-t', '--target', help='Target function in the segment')
    parser.add_argument('-c', '--clang-args', help='Arguments to clang (e.g. -I..., -W...)', default='')
    args = parser.parse_args()
    return args

def is_the_same(orig_cursor, seg_cursor):
    """
    Compare a cursor from the original and the segment to see if they refer to the same function in the project
    """

    return seg_cursor.spelling == f'helium_{orig_cursor.spelling}'

def select_target(cur, target_name=None):
    """
    Select a target function from a cursor
    """
    func_decls = find(cur, CursorKind.FUNCTION_DECL)
    if target_name:
        # Select the function matching a name
        try:
            return next(filter(lambda f: f.spelling == target_name, func_decls))
        except:
            log.exception(f'could not find target function with name {target_name}')
            raise
    else:
        # Select the last eligible function based on heuristic
        eligible = filter(lambda f: '.c' in f.location.file.name and f.spelling != 'main', func_decls)
        return max(eligible, key=lambda f: f.location.line)

def gen_printfs(parms, arrays={}):
    """
    Generate printf statements for a set of function parmameters, otherwise leave a to do comment
    """
    def genny(name, t, stack=[]):
        if t.kind == TypeKind.TYPEDEF:
            t = t.get_canonical()

        log.debug(f'name {name} type kind {t.kind}')

        if t.kind == TypeKind.POINTER:
            name = f'*{name}'
        yield f'print {name}'

    for p in parms:
        yield from genny(p.spelling, p.type)

if __name__ == "__main__":
    main()

