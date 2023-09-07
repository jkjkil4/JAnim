from __future__ import annotations

import os
import tempfile

from janim.utils.file_ops import guarantee_existence
from janim.config import get_configuration

def get_temp_dir() -> str:
    return (
        get_configuration()['directories']['temporary_storage']
        or tempfile.gettempdir()
    )

def get_item_data_dir() -> str:
    return guarantee_existence(os.path.join(get_temp_dir(), 'item_data'))
