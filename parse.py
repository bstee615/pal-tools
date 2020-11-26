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

def find_funcdecls(node):
    """
    Return all function declarations
    """

    if node.kind == CursorKind.FUNCTION_DECL:
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find_funcdecls(child)

def find_structs(node):
    """
    Return all struct decls
    """

    if node.kind == CursorKind.STRUCT_DECL:
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find_structs(child)

def find_parmdecls(node):
    """
    Return all parameter decls in function decl
    """

    # print(pp(node))

    if node.kind == CursorKind.PARM_DECL:
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find_parmdecls(child)

def main():
    filename = 'main.c'

    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    print('Translation unit:', tu.spelling)
    
    cur = tu.cursor

    structs = find_structs(cur)
    spellings_structs = ((n.spelling, n) for n in structs)
    structs_by_spelling = dict(spellings_structs)
    print(pp(structs_by_spelling['f']))

    funcdefs = find_funcdecls(cur)
    last_funcdef = max(funcdefs, key=lambda n: n.location.file.name == filename and n.location.line)
    print(f'last: {pp(last_funcdef)}')

    for i in find_parmdecls(last_funcdef):
        print(pp(i))

if __name__ == "__main__":
    main()
