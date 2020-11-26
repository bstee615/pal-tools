#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex
from clang.cindex import CursorKind

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

def main():
    filename = 'main.c'

    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    print('Translation unit:', tu.spelling)
    
    cur = tu.cursor

    structs = find(cur, CursorKind.STRUCT_DECL)
    spellings_structs = ((n.spelling, n) for n in structs)
    structs_by_spelling = dict(spellings_structs)
    print(pp(structs_by_spelling['f']))

    funcdefs = find(cur, CursorKind.FUNCTION_DECL)
    last_funcdef = max(funcdefs, key=lambda n: n.location.file.name == filename and n.location.line)
    print(f'last: {pp(last_funcdef)}')

    for child in find(last_funcdef, CursorKind.PARM_DECL):
        print(pp(child))

if __name__ == "__main__":
    main()
