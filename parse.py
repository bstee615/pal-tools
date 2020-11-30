#!/bin/python3

""" Find all usages of some type
"""

import clang.cindex
from clang.cindex import CursorKind, TypeKind

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

from dataclasses import dataclass
from typing import Any
@dataclass
class LocalVariable:
    type: Any = None
    name: Any = None
    children: Any = 0

def local_vars(type, varname):
    """
    Yields input variables for type t's fields, down to primitives
    """

    if type.kind == TypeKind.ELABORATED:
        td = type.get_declaration()
        children = list(td.get_children())
        for fd in children:
            yield from local_vars(fd.type, fd.displayname)
        yield LocalVariable(type, varname, len(children))
    elif type.kind == TypeKind.POINTER:
        # TODO: Currently inits all ptrs as single values. What about arrays?
        yield from local_vars(type.get_pointee(), f'{varname}_v')
        yield LocalVariable(type, varname, 1)
    elif type.kind == TypeKind.INT:
        yield LocalVariable(type, varname)
    elif type.kind == TypeKind.CHAR_S:
        yield LocalVariable(type, varname)
    else:
        print('local variables unhandled kind', type.kind)

def initializers(vars):
    """
    Yields C statements to declare and read values for input vars.
    """
    
    def declare(v):
        return f'{v.type.spelling} {v.name};'
        
    def read_and_assign(i, v):
        vars_so_far = vars[:i]
        if v.type.kind == TypeKind.ELABORATED:
            for c in reversed(vars_so_far[:-v.children]):
                return f'{v.name}.{c.name} = {c.name};'
        elif v.type.kind == TypeKind.POINTER:
            # TODO: Currently inits all ptrs as single values. What about arrays?
            return f'{v.name} = &{vars_so_far[-v.children].name};'
        elif v.type.kind == TypeKind.INT:
            return f'scanf("%d", &{v.name});'
        elif v.type.kind == TypeKind.CHAR_S:
            return f'scanf(" %c", &{v.name});'
        else:
            print('definitions unhandled kind', type.kind)

    for i, v in enumerate(vars):
        yield (declare(v), read_and_assign(i, v))

def main():
    filename = 'main.c'

    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    print('Translation unit:', tu.spelling)
    
    cur = tu.cursor

    funcdefs = find(cur, CursorKind.FUNCTION_DECL)
    last_funcdef = max(funcdefs, key=lambda n: n.location.file.name == filename and n.location.line)
    print(f'last: {pp(last_funcdef)}')

    parmesan = list(find(last_funcdef, CursorKind.PARM_DECL))
    for parm in parmesan:
        locals = list(local_vars(parm.type, parm.displayname))
        print(parm.type.spelling, pp(parm), locals)
        
        inits = list(initializers(locals))

        decls, defs = zip(*inits)
        print(decls)
        print(defs)

    print(f'{last_funcdef.spelling}({", ".join(p.displayname for p in parmesan)})')

if __name__ == "__main__":
    main()
