import pytest
import clang.cindex
from clang.cindex import CursorKind
from harn import find, initializers, local_vars

@pytest.fixture
def test_file():
    index = clang.cindex.Index.create()
    filename = 'fn.c'
    text = '''
struct foo
{
    int x;
    char *y;
};

int fn(int a, char b, struct foo c) {
    return a + b + c.x;
}
'''
    tu = index.parse(path=filename, unsaved_files=[(filename, text)])
    return tu

def test_find(test_file):
    cur = test_file.cursor
    fn_decls = list(find(cur, CursorKind.FUNCTION_DECL))

    assert len(fn_decls) == 1
    assert fn_decls[0].spelling == 'fn'

    fn = fn_decls[0]

    parm_decls = list(find(fn, CursorKind.PARM_DECL))

    assert len(parm_decls) == 3
    assert parm_decls[0].spelling == 'a'
    assert parm_decls[0].type.spelling == 'int'
    assert parm_decls[1].spelling == 'b'
    assert parm_decls[1].type.spelling == 'char'
    assert parm_decls[2].spelling == 'c'
    assert parm_decls[2].type.spelling == 'struct foo'

    a_decl, b_decl, c_decl = parm_decls

    a_locals = list(local_vars(a_decl.type, a_decl.displayname))
    assert len(a_locals) == 1
    assert a_locals[0].name == 'a'
    assert a_locals[0].type.spelling == 'int'
    assert a_locals[0].children == 0

    b_locals = list(local_vars(b_decl.type, b_decl.displayname))
    assert len(b_locals) == 1
    assert b_locals[0].name == 'b'
    assert b_locals[0].type.spelling == 'char'
    assert b_locals[0].children == 0

    c_locals = list(local_vars(c_decl.type, c_decl.displayname))
    assert len(c_locals) == 3
    assert c_locals[0].name == 'x'
    assert c_locals[0].type.spelling == 'int'
    assert c_locals[0].children == 0
    assert c_locals[1].name == 'y'
    assert c_locals[1].type.spelling == 'char *'
    assert c_locals[1].children == 0
    assert c_locals[2].name == 'c'
    assert c_locals[2].type.spelling == 'struct foo'
    assert c_locals[2].children == 2

    c_inits = list(initializers(c_locals))
    assert len(c_inits) == 3
    assert c_inits[0][0] == 'int x;'
    assert 'atoi' in c_inits[0][1]
    assert c_inits[1][0] == 'char * y;'
    assert 'strcpy' in c_inits[1][1]
    assert c_inits[2][0] == 'struct foo c;'
    assert 'c.y = y;' in c_inits[2][1] and 'c.x = x;' in c_inits[2][1]
