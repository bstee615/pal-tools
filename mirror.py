
import clang.cindex
from clang.cindex import CursorKind, TypeKind

import logging
import sys
import difflib
import argparse

log = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
verbose_fmt = logging.Formatter('%(levelname)s - %(message)s')
stdout_handler.setFormatter(verbose_fmt)
log.addHandler(stdout_handler)
log.setLevel(logging.DEBUG)

verbose = False

def pp(node):
    """
    Return str of node for pretty print
    """
    return f'{node.displayname} ({node.kind}) [{node.location}]'

def loc(cur, link=True):
    """
    Return file location of cursor
    """
    if link:
        return f'{cur.location.file.name}:{cur.location.line}'
    else:
        return cur.location.file.name, cur.location.line

def find(node, kind):
    """
    Return all node's descendants of a certain kind
    """

    if verbose:
        log.debug(f'find: walked node {pp(node)}')

    if node.kind == kind:
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find(child, kind)

def main():
    log.setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('segment_file')
    parser.add_argument('original_file')
    parser.add_argument('-l', '--log-level', help='Display logs at a certain level (DEBUG, INFO, ERROR)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose logs. Should be used in tandem with "-l DEBUG"')
    parser.add_argument('-a', '--array', action='append', default=[], help='Assign length expressions for array variables. Length expressions are in the format "array:length", where array is the name of the array and length is a C expression to be evaluated at runtime, typically a number or variable reference')
    parser.add_argument('-t', '--target', help='Target function in the segment')
    parser.add_argument('-c', '--clang-args', help='Arguments to clang (e.g. -I..., -W...)', default='')
    args = parser.parse_args()

    if args.log_level:
        log.setLevel(args.log_level)
        log.debug(f'setting log level to {args.log_level}')

    seg_c = args.segment_file
    orig_c = args.original_file
    log.debug(f'segment: {seg_c}, original: {orig_c}')

    clang_args = args.clang_args.split()
    if clang_args:
        log.debug(f' provided clang args: {clang_args}')

    if args.verbose:
        global verbose
        verbose = True
        log.debug(f'verbose logging enabled')

    index = clang.cindex.Index.create()
    seg_tu = index.parse(seg_c, args=clang_args)
    seg_cur = seg_tu.cursor
    seg_target = select_target(seg_cur, target_name=args.target)
    parms = find(seg_target, CursorKind.PARM_DECL)
    
    orig_tu = index.parse(orig_c)
    orig_cur = orig_tu.cursor
    orig_target = next(filter(lambda f: is_the_same(f, seg_target), find(orig_cur, CursorKind.FUNCTION_DECL)))
    orig_target_def = orig_target.get_definition()
    first_stmt = next(filter(lambda c: c.kind.is_statement(), orig_target_def.get_children()))
    first_stmt_file, first_stmt_line = loc(first_stmt, link=False)
    with open(first_stmt_file, 'r') as f:
        fromlines = f.readlines()

    arrays = dict(a.split(':') for a in args.array)
    printfs = list(f'{p}\n' for p in gen_printfs(parms, arrays))
    tolines = fromlines[:first_stmt_line] + printfs + fromlines[first_stmt_line:]

    patchfile = first_stmt_file
    for fi, fp in enumerate(first_stmt_file.split('/'), start=1):
        for sp in seg_c.split('/'):
            if fp == sp:
                patchfile = '/'.join(first_stmt_file.split('/')[fi:])
                log.debug(f'patching {patchfile}')

    diff = difflib.unified_diff(fromlines, tolines, fromfile=patchfile, tofile=patchfile)
    print(''.join(diff))

def is_the_same(orig_cursor, seg_cursor):
    """
    Compare a cursor from the original and the segment to see if they refer to the same function in the project
    """
    return orig_cursor.spelling in seg_cursor.spelling

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
    def genny(name, t):
        yield f'// name {name} type kind {t.kind}'
        if t.kind == TypeKind.INT or \
            t.kind == TypeKind.SHORT or \
            t.kind == TypeKind.LONG or \
            t.kind == TypeKind.LONGLONG or \
            t.kind == TypeKind.INT128:
            yield f'printf("benjis:{name}:%d\\n", {name});'
        elif t.kind == TypeKind.UINT or \
            t.kind == TypeKind.ULONG or \
            t.kind == TypeKind.ULONGLONG or \
            t.kind == TypeKind.UINT128:
            yield f'printf("benjis:{name}:%u\\n", {name});'
        elif t.kind == TypeKind.ELABORATED:
            for c in t.get_fields():
                yield from genny(f'{name}.{c.spelling}', c.type)
        elif t.kind == TypeKind.POINTER:
            if t.get_pointee().kind == TypeKind.CHAR_S:
                yield f'printf("benjis:{name}:%s\\n", {name});'
            else:
                array = False
                for key in arrays:
                    if key == name:
                        array = True
                        i_name = f'{name}_benjis_i'
                        yield f'for(int {i_name} = 0; {i_name} < {arrays[name]}; {i_name} ++)'
                        yield '{'
                        yield from genny(f'{name}[{i_name}]', t.get_pointee())
                        yield '}'
                if not array:
                    yield from genny(f'(*{name})', t.get_pointee())
        elif t.kind == TypeKind.CHAR_S:
            yield f'printf("benjis:{name}:%c\\n", {name});'
        else:
            yield f'// TODO benjis: print {name}'

    for p in parms:
        yield from genny(p.spelling, p.type)

if __name__ == "__main__":
    main()

