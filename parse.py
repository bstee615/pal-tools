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

    if node.location.file and node.location.file.name == 'main.c':
        if node.kind == CursorKind.FUNCTION_DECL:
            print(f'function decl {pp(node)}]')
            yield node
    # Recurse for children of this node
    for child in node.get_children():
        yield from find_funcdefs(child)

def main():
    filename = 'main.c'

    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    print('Translation unit:', tu.spelling)

    cur = tu.cursor
    funcdefs = find_funcdefs(cur)
    last_funcdef = max(funcdefs, key=lambda n: n.location.line)
    print(f'last: {pp(last_funcdef)}')

if __name__ == "__main__":
    main()
