
# import pkg_resources
# __version__ = pkg_resources.get_distribution("janim").version

__version__ = '0.1'

from janim.animation.animation import *
from janim.animation.composition import *
from janim.animation.creation import *
from janim.animation.fading import *
from janim.animation.growing import *
from janim.animation.indication import *
from janim.animation.movement import *
from janim.animation.rotation import *
from janim.animation.transform import *

from janim.items.geometry.arc import *
from janim.items.geometry.arrow import *
from janim.items.geometry.line import *
from janim.items.geometry.polygon import *
from janim.items.text.pixel_text import *
from janim.items.text.tex import *
from janim.items.text.text import *
from janim.items.dot_cloud import *
from janim.items.img_item import *
from janim.items.item import *
from janim.items.number_line import *
from janim.items.numbers import *
from janim.items.shape_matchers import *
from janim.items.svg_item import *
from janim.items.value_tracker import *
from janim.items.vitem import *

from janim.utils.rate_functions import *

from janim.constants import *

from janim.scene.scene import *
