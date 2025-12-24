import sys

try:
    import PySide6  # noqa: F401
except ImportError:
    from janim.locale.i18n import get_translator
    _ = get_translator('janim.gui.anim_viewer')

    print(_('Additional modules need to be installed when using the GUI interface, but they are not installed'),
          file=sys.stderr)
    print(_('You can install them using pip install "janim[gui]" '
            'and make sure you install them in the correct Python version'),
          file=sys.stderr)

    from janim.exception import EXITCODE_PYSIDE6_NOT_FOUND, ExitException
    raise ExitException(EXITCODE_PYSIDE6_NOT_FOUND)
