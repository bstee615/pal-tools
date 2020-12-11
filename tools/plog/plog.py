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
    orig_c = args.original_file
    log.debug(f'segment: {seg_c}, original: {orig_c}')

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
    
    orig_cur = parse(orig_c)
    orig_funcdecls = find(orig_cur, CursorKind.FUNCTION_DECL)
    orig_target = next(f.get_definition() for f in orig_funcdecls if is_the_same(f, seg_target))
    orig_body = find(orig_target, lambda c: c.kind.is_statement())
    first_stmt = next(iter(orig_body))
    first_stmt_file, first_stmt_line = first_stmt.location.file.name, first_stmt.location.line

    diff = gen_patch(first_stmt_file, first_stmt_line, parms, args.array)
    print(''.join(diff))

def gen_patch(file, line, parms, array_expressions):
    with open(file, 'r') as f:
        fromlines = f.readlines()

    arrays = dict(a.split(':') for a in array_expressions)
    log.debug(f'{len(parms)} parameters')
    printfs = list(f'{p}\n' for p in gen_printfs(parms, arrays))
    tolines = fromlines[:line] + printfs + fromlines[line:]

    return difflib.unified_diff(fromlines, tolines, fromfile=file, tofile=file)

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

        yield f'// name {name} type kind {t.kind}'
        log.debug(f'name {name} type kind {t.kind}')
        log.debug(f'stack: {[pp(s) for s in stack]}')

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
        elif t.kind == TypeKind.ELABORATED or t.kind == TypeKind.RECORD:
            if t not in stack:
                log.debug(f'{len(list(t.get_fields()))} fields')
                for c in t.get_fields():
                    yield from genny(f'{name}.{c.spelling}', c.type, stack + [t])
            else:
                yield f'// TODO benjis: print recursive struct member {name}'
        elif t.kind == TypeKind.POINTER:
            yield f'if ({name}) {{'

            if t.get_pointee().kind == TypeKind.CHAR_S:
                yield f'printf("benjis:{name}:%s\\n", {name});'
            else:
                array = False
                for key in arrays:
                    if key == name:
                        array = True
                        i_name = f'{name.replace(".", "_").replace("*", "_").replace("(", "_").replace(")", "_")}_benjis_i'
                        yield f'for(int {i_name} = 0; {i_name} < {arrays[name]}; {i_name} ++)'
                        yield '{'
                        yield from genny(f'{name}[{i_name}]', t.get_pointee(), stack + [t])
                        yield '}'
                if not array:
                    yield from genny(f'(*{name})', t.get_pointee(), stack + [t])

            yield f'}}'
            yield f'else {{'
            yield f'printf("benjis:{name}:(null)\\n");'
            yield f'}}'
        elif t.kind == TypeKind.ENUM:
            yield f'printf("benjis:{name}:%d\\n", {name});'
        elif t.kind == TypeKind.CHAR_S:
            yield f'printf("benjis:{name}:%c\\n", {name});'
        elif t.kind == TypeKind.CONSTANTARRAY:
            size = t.get_array_size() # bless up
            i_name = f'{name.replace(".", "_").replace("*", "_").replace("(", "_").replace(")", "_")}_benjis_i'
            yield f'for(int {i_name} = 0; {i_name} < {size}; {i_name} ++)'
            yield '{'
            yield from genny(f'{name}[{i_name}]', t.get_array_element_type(), stack + [t])
            yield '}'
        else:
            yield f'// TODO benjis: print {name}'

    for p in parms:
        yield from genny(p.spelling, p.type)

if __name__ == "__main__":
    main()

