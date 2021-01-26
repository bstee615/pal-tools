import unittest
from tools.trace.trace import parse_args
import argparse

arg_sets = [
    (["trace", "--", "data/coreutils.7eff5901/coreutils-assert/src/expr", "2", "+", "-4"], ["data/coreutils.7eff5901/coreutils-assert/src/expr", "2", "+", "-4"],),
    (["trace", "--", "data/test", "dir1", "directory2", "-printf", "'%H %P\n'"], ["data/test", "dir1", "directory2", "-printf", "'%H %P\n'"],),
    (["trace", "--", "data/test dir1 directory2 -printf '%H %P\n'"], ["data/test dir1 directory2 -printf '%H %P\n'"],),
    # (["trace", "g"], None,),
    # (["trace", "-g goo"], None,),
    (["trace", "--", "g"], ['g'],),
]

class TestArgParse(unittest.TestCase):

    def test_target_args(self):
        for argv, expected in arg_sets:
            print(argv, expected)
            if expected is None:
                with self.assertRaises(SystemExit) as cm:
                    args = parse_args(argv, do_wizard=False)
                self.assertEqual(cm.exception.code, 2)
            args = parse_args(argv, do_wizard=False)
            self.assertListEqual(expected, args.target)

if __name__ == '__main__':
    unittest.main()
