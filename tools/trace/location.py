from collections import namedtuple
Location = namedtuple('Location', 'filepath lineno column')
SlimLocation = namedtuple('SlimLocation', 'filepath lineno')
