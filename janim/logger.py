import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

__all__ = ['log', 'plog']


FORMAT = "%(message)s"
logging.basicConfig(level=logging.WARNING)

log = logging.getLogger('janim')
log.propagate = False
if not log.hasHandlers():
    fmt = logging.Formatter("%(message)s", datefmt="[%X]")
    rich_handler = RichHandler(console=Console(stderr=True))    # RichHandler 默认输出到 stdout，需要手动改为 stderr
    rich_handler.setFormatter(fmt)
    log.addHandler(rich_handler)
log.setLevel('INFO')

plog = logging.getLogger('janim.plain')
plog.propagate = False
if not plog.hasHandlers():
    handler = logging.StreamHandler(sys.stderr)
    plog.addHandler(handler)
plog.setLevel('INFO')
