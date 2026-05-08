import os

from qdarkstyle import (
    DarkPalette,
    _apply_application_patches,
    _apply_binding_patches,
    _apply_os_patches,
    _apply_version_patches,
)

from janim.utils.file_ops import get_janim_dir, readall


def load_stylesheet() -> str:
    """
    qdarkstyle.load_stylesheet_pyside6 的覆盖实现

    将 ``qrc`` 加载逻辑替换为了直接读取 ``styles.qss`` ，避免在某些系统上加载崩溃
    """
    os.environ['QT_API'] = 'pyside6'

    from PySide6.QtCore import qVersion, QCoreApplication
    from PySide6.QtGui import QColor, QPalette

    #
    from qdarkstyle.dark import darkstyle_rc  # noqa

    palette = DarkPalette

    # load stylesheet
    qss_file = os.path.join(get_janim_dir(), 'gui', 'qdarkstyle', 'styles.qss')
    stylesheet = readall(qss_file)

    # 1. Apply OS specific patches
    stylesheet += _apply_os_patches(palette)

    # 2. Apply binding specific patches
    stylesheet += _apply_binding_patches()

    # 3. Apply binding version specific patches
    stylesheet += _apply_version_patches(qVersion())

    # 4. Apply palette fix. See issue #139
    _apply_application_patches(QCoreApplication, QPalette, QColor, palette)

    return stylesheet
