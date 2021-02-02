import logging
from tools.trace.location import Location
from tools.trace.trace import debug_print_code, get_static_locations
import unittest
import nodeutils
from pathlib import Path

from clang import cindex

def get_node(file, function_name, clang_args=[]):
    index = cindex.Index.create()
    translation_unit = index.parse(file, args=clang_args)
    with open(file) as f:
        source_index = f.read().index(function_name)
    file = cindex.File.from_name(translation_unit, file)
    location = cindex.SourceLocation.from_offset(translation_unit, file, source_index)
    node = cindex.Cursor.from_location(translation_unit, location)
    assert node.kind == cindex.CursorKind.FUNCTION_DECL
    return node


def get_testpath(filepath):
    """
    Validate and return the path to a test file or directory
    """
    root = Path(__file__).resolve().parent
    testfile = root / filepath
    assert testfile.is_file() or testfile.is_dir()
    return str(testfile)


def smorg_lines():
    filename = get_testpath('tests/smorg.c')
    smorg = get_node(filename, 'smorgasboard')

    smorg_loc = Location(smorg.location.file.name, smorg.location.line, smorg.location.column)
    static_locations = get_static_locations([smorg_loc], [])

    debug_code = debug_print_code(static_locations)
    _, lines = zip(*debug_code[filename])
    return lines

class TestStaticInfo(unittest.TestCase):

    def test_gets_vardecls(self):
        lines = smorg_lines()
        assert any('int a' in l for l in lines)
        assert any('int b' in l for l in lines)
        assert any('int c' in l for l in lines)

    def test_gets_cases(self):
        lines = smorg_lines()
        assert any('case 0' in l for l in lines)
        assert any('case 1' in l for l in lines)
        assert any('case 253' in l for l in lines)

    def test_gets_defaults(self):
        lines = smorg_lines()
        assert any('default' in l for l in lines)

    def test_gets_static_info_only_from_target_function(self):
        filename = get_testpath('tests/picky.c')
        boo = get_node(filename, 'boo')

        boo_loc = Location(boo.location.file.name, boo.location.line, boo.location.column)
        static_locations = get_static_locations([boo_loc], [])

        debug_code = debug_print_code(static_locations)
        _, lines = zip(*debug_code[filename])
        assert any('boo_var' in l for l in lines)
        assert any('// boo' in l for l in lines)
        assert not any('foo_var' in l for l in lines)
        assert not any('// foo' in l for l in lines)

    def test_hidden_includes(self):
        filename = get_testpath('tests/includeme.c')
        fn = get_node(filename, 'main')

        fn_loc = Location(fn.location.file.name, fn.location.line, fn.location.column)
        static_locations = get_static_locations([fn_loc], [])
        debug_code = debug_print_code(static_locations)
        assert len(debug_code) == 0
        
        fn_loc = Location(fn.location.file.name, fn.location.line, fn.location.column)
        static_locations = get_static_locations([fn_loc], [f'-I{get_testpath("tests/hidden")}'])
        debug_code = debug_print_code(static_locations)
        assert len(debug_code) > 0
        _, lines = zip(*debug_code[filename])
        assert any('mytype i;' in l for l in lines)


if __name__ == '__main__':
    unittest.main()
