'''
使用 ``from janim.imports import *`` 即可导入 ``janim`` 主要的功能
'''

# flake8: noqa
from colour import Color

import janim.items.boolean_ops as boolean_ops
from janim.anims.composition import *
from janim.anims.creation import *
from janim.anims.display import *
from janim.anims.fading import *
from janim.anims.growing import *
from janim.anims.indication import *
from janim.anims.movement import *
from janim.anims.rotation import *
from janim.anims.timeline import *
from janim.anims.transform import *
from janim.anims.updater import *
from janim.camera.camera import *
from janim.camera.camera_info import *
from janim.components.rgbas import apart_alpha, merge_alpha
from janim.constants import *
from janim.exception import *
from janim.items.audio import *
from janim.items.coordinate.coordinate_systems import *
from janim.items.coordinate.functions import *
from janim.items.coordinate.number_line import *
from janim.items.frame_effect import *
from janim.items.geometry.arc import *
from janim.items.geometry.arrow import *
from janim.items.geometry.line import *
from janim.items.geometry.polygon import *
from janim.items.image_item import *
from janim.items.item import *
from janim.items.points import *
from janim.items.shape_matchers import *
from janim.items.svg.brace import *
from janim.items.svg.svg_item import *
from janim.items.svg.typst import *
from janim.items.svg.typst_types import *
from janim.items.text import *
from janim.items.value_tracker import *
from janim.items.vitem import *
from janim.typing import *
from janim.utils.bezier import *
from janim.utils.config import Config
from janim.utils.file_ops import *
from janim.utils.iterables import *
from janim.utils.paths import *
from janim.utils.rate_functions import *
from janim.utils.reload import reloads
from janim.utils.simple_functions import *
from janim.utils.space_ops import *
