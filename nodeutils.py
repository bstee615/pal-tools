"""
Utilities for nodes (cursors) in the Clang AST
"""

from clang.cindex import CursorKind
from mylog import log
import clang


def pp(node):
    """
    Return str of node for pretty print
    """
    try:
        return f'{node.spelling} ({node.kind}) [{node.location}]'
    except:
        return f'{node.spelling} ({node.kind})'


def find(node, selector, verbose=False):
    """
    Return all node's descendants of a certain kind
    """

    if verbose:
        log.debug(f'find: walked node {pp(node)}')

    found = []

    if isinstance(selector, CursorKind):
        if node.kind == selector:
            found.append(node)
    elif callable(selector):
        if selector(node):
            found.append(node)

    # Recurse for children of this node
    for child in node.get_children():
        found += find(child, selector, verbose)

    return found


class GlobalIndex:
    """
    Singleton Clang Index
    """

    def __init__(self):
        self.index = clang.cindex.Index.create()

    _instance = None

    @classmethod
    def get():
        if GlobalIndex._instance is None:
            GlobalIndex._instance = GlobalIndex()
        return GlobalIndex._instance


def parse(filepath, args=[]):
    """
    Parse filepath and return a cursor to the translation unit
    """
    index = GlobalIndex.get()
    translation_unit = index.parse(filepath, args=args)
    return translation_unit.cursor
