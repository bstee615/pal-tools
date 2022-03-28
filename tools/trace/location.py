from collections import namedtuple
Location = namedtuple('Location', 'filepath lineno column node')


class Location:
    def __init__(self, filepath, lineno, column, node=None):
        self.filepath = filepath
        self.lineno = lineno
        self.column = column
        self.node = node

    def __repr__(self):
        return f'{self.filepath}:{self.lineno}:{self.column} {self.node.spelling if self.node else None}'


SlimLocation = namedtuple('SlimLocation', 'filepath lineno column code')
