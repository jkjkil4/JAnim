import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

__all__ = ['log']


class Filter(logging.Filter):
    def __init__(self, callback):
        self.callback = callback

    def filter(self, record):
        return self.callback(record)


logging.basicConfig(level=logging.WARNING)

log = logging.getLogger('janim')
log.propagate = False
log.setLevel('INFO')

if not log.hasHandlers():
    fmt = logging.Formatter("%(message)s", datefmt="[%X]")
    rich_handler = RichHandler(console=Console(stderr=True))    # RichHandler 默认输出到 stdout，需要手动改为 stderr
    rich_handler.setFormatter(fmt)
    rich_handler.addFilter(Filter(lambda record: not getattr(record, 'raw', False)))
    log.addHandler(rich_handler)

    plain_handler = logging.StreamHandler(sys.stderr)
    plain_handler.addFilter(Filter(lambda record: getattr(record, 'raw', False)))
    log.addHandler(plain_handler)
