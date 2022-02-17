from collections import namedtuple
Location = namedtuple('Location', 'filepath lineno column node')
class Location:
    def __init__(self, filepath, lineno, column, node = None):
        self.filepath = filepath
        self.lineno = lineno
        self.column = column
        self.node = node
SlimLocation = namedtuple('SlimLocation', 'filepath lineno column code')
