#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex

def find_typerefs(node, typename):
    """ Find all references to the type named 'typename'
    """
    if node.kind.is_reference():
        ref_node = node.referenced
        if ref_node.spelling == typename:
            print('Found %s [line=%s, col=%s]' % (
                typename, node.location.line, node.location.column))
    # Recurse for children of this node
    for c in node.get_children():
        find_typerefs(c, typename)

filename = 'main.cpp'
typename = 'Person'

index = clang.cindex.Index.create()
tu = index.parse(filename)
print('Translation unit:', tu.spelling)

cur = tu.cursor
print(cur.spelling)
find_typerefs(cur, typename)
