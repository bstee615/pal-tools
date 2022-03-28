import logging
import sys

"""
Common logger
"""

log = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
verbose_fmt = logging.Formatter('%(levelname)s - %(message)s')
stdout_handler.setFormatter(verbose_fmt)
log.addHandler(stdout_handler)
log.setLevel(logging.ERROR)


class CappedLog:
    """Cap the number of logs to a fixed limit and note a message when the limit is hit."""

    def __init__(self, limit=100, log_fn=log.debug) -> None:
        self.count = 0
        self.limit = limit
        self.log = log_fn

    def __call__(self, *args, **kwargs):
        if self.count < self.limit:
            self.log(*args, **kwargs)
        if self.count == self.limit - 1:
            self.log(f'^^^ CAPPING this log at {self.limit} items ^^^')
        self.count += 1
