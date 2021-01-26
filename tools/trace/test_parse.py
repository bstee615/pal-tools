import logging
from tools.trace.location import Location
from tools.trace.trace import debug_print_code, get_static_locations
import unittest
import nodeutils

from clang import cindex

def get_node(file, function_name):
    index = cindex.Index.create()
    translation_unit = index.parse(file)
    with open(file) as f:
        source_index = f.read().index(function_name)
    file = cindex.File.from_name(translation_unit, file)
    location = cindex.SourceLocation.from_offset(translation_unit, file, source_index)
    node = cindex.Cursor.from_location(translation_unit, location)
    assert node.kind == cindex.CursorKind.FUNCTION_DECL
    return node

class TestStaticInfo(unittest.TestCase):

    def test_gets_static_info(self):
        filename = 'data/tests/smorg.c'
        smorg = get_node(filename, 'smorgasboard')

        smorg_loc = Location(smorg.location.file.name, smorg.location.line, smorg.location.column)
        static_locations = get_static_locations([smorg_loc])

        debug_code = debug_print_code(static_locations)
        _, lines = zip(*debug_code[filename])
        print(lines)
        assert len(lines) == 7
        assert any('int a' in l for l in lines)
        assert any('int b' in l for l in lines)
        assert any('int c' in l for l in lines)
        assert any('case 0' in l for l in lines)
        assert any('case 1' in l for l in lines)
        assert any('case 253' in l for l in lines)
        assert any('default' in l for l in lines)

    def test_gets_static_info_only_from_target_function(self):
        filename = 'data/tests/picky.c'
        boo = get_node(filename, 'boo')

        boo_loc = Location(boo.location.file.name, boo.location.line, boo.location.column)
        static_locations = get_static_locations([boo_loc])

        debug_code = debug_print_code(static_locations)
        _, lines = zip(*debug_code[filename])
        print(lines)
        assert len(lines) == 1
        assert any('boo_var' in l for _, l in lines)
        assert not any('foo_var' in l for _, l in lines)


if __name__ == '__main__':
    unittest.main()
