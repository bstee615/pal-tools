#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex
from clang.cindex import CursorKind

def pp(node):
    """
    Return str of node for pretty print
    """
    return f'{node.displayname} [{node.location}]'

def find_funcdefs(node):
    """
    Return all function declarations
    """

    if node.kind == CursorKind.FUNCTION_DECL:
        # print(f'function decl {pp(node)}]')
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find_funcdefs(child)

def find_structs(node):
    """
    Return all structs
    """

    if node.kind == CursorKind.STRUCT_DECL:
        # print(f'struct decl {pp(node)}]')
        yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find_structs(child)

def main():
    filename = 'main.c'

    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    print('Translation unit:', tu.spelling)

    cur = tu.cursor
    funcdefs = find_funcdefs(cur)
    last_funcdef = max(funcdefs, key=lambda n: n.location.file.name == filename and n.location.line)
    print(f'last: {pp(last_funcdef)}')

    structs = find_structs(cur)
    for s in filter(lambda n: n.location.file.name == filename, structs):
        print(pp(s))

if __name__ == "__main__":
    main()
