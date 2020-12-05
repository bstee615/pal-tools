
import clang.cindex
from clang.cindex import CursorKind, TypeKind

import logging
import sys
import difflib

log = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
verbose_fmt = logging.Formatter('%(levelname)s - %(message)s')
stdout_handler.setFormatter(verbose_fmt)
log.addHandler(stdout_handler)
log.setLevel(logging.DEBUG)

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

    log.debug(f'find: walked node {pp(node)}')

    if node.kind == kind:
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find(child, kind)

def main():
    log.setLevel(logging.INFO)

    index = clang.cindex.Index.create()
    seg_tu = index.parse('seg/main.c')
    seg_cur = seg_tu.cursor
    seg_target = select_target(seg_cur, target_name='helium_sum')
    parms = find(seg_target, CursorKind.PARM_DECL)
    
    orig_tu = index.parse('orig/main.c')
    orig_cur = orig_tu.cursor
    orig_target = next(filter(lambda f: f.spelling in seg_target.spelling, find(orig_cur, CursorKind.FUNCTION_DECL)))
    orig_target_def = orig_target.get_definition()
    first_stmt = next(filter(lambda c: c.kind.is_statement(), orig_target_def.get_children()))
    first_stmt_file, first_stmt_line = loc(first_stmt, link=False)
    with open(first_stmt_file, 'r') as f:
        fromlines = f.readlines()

    printfs = [f'// TODO benjis: print {p.spelling}\n' for p in parms]
    tolines = fromlines[:first_stmt_line] + printfs + fromlines[first_stmt_line:]

    diff = difflib.unified_diff(fromlines, tolines, fromfile=first_stmt_file, tofile=first_stmt_file)
    print(''.join(diff))

def select_target(cur, target_name=None):
    """
    Select a target function from a cursor
    """
    func_decls = find(cur, CursorKind.FUNCTION_DECL)
    if target_name:
        # Select the function matching a name
        return next(filter(lambda f: f.spelling == target_name, func_decls))
    else:
        # Select the last function to occur in a .c file
        return max(func_decls, key=lambda f: f.location.line if '.c' in f.location.file.name else -1)

if __name__ == "__main__":
    main()

