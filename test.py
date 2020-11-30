import pytest
import clang.cindex
from clang.cindex import CursorKind
from parse import find

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
