import clang.cindex
from clang.cindex import CursorKind
from parse import find

def test_find():
    index = clang.cindex.Index.create()
    file = ('fn.c', 'int fn(int a, char b) { }')
    tu = index.parse(path='fn.c', unsaved_files=[file])
    print('translation unit:', tu.spelling)

    fn_decls = list(find(tu.cursor, CursorKind.FUNCTION_DECL))

    assert len(fn_decls) == 1
    assert fn_decls[0].spelling == 'fn'

    parm_decls = list(find(tu.cursor, CursorKind.PARM_DECL))

    assert len(parm_decls) == 2
    assert parm_decls[0].spelling == 'a'
    assert parm_decls[0].type.spelling == 'int'
    assert parm_decls[1].spelling == 'b'
    assert parm_decls[1].type.spelling == 'char'
