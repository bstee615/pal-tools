#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex
from clang.cindex import CursorKind

def find_typerefs(node, typename):
    """ Find all references to the type named 'typename'
    """
    print(node.kind, node.spelling)

    if node.location.file and node.location.file.name == 'main.c':
        if node.kind.is_reference():
            if node.spelling == typename:
                print('Found %s [file=%s, line=%s, col=%s]' % (
                    typename, node.location.file, node.location.line, node.location.column))
    # Recurse for children of this node
    for c in node.get_children():
        find_typerefs(c, typename)

def main():
    filename = 'main.c'
    typename = '__int8_t'

    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    print('Translation unit:', tu.spelling)
    tu.save('tmp.c')

    cur = tu.cursor
    find_typerefs(cur, typename)

if __name__ == "__main__":
    main()
