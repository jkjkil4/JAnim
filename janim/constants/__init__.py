from typing import Union, Iterable
import ctypes
import numpy as np
import colour
from enum import Enum

from janim.constants.colors import *

class JointType(Enum):
    Auto = 0
    Bevel = 1
    Sharp = 2

class AnchorMode(Enum):
    Jagged = 0
    ApproxSmooth = 1
    TrueSmooth = 2

class InputSampleType(Enum):
    Left = 0
    Right = 1
    Center = 2

FFMPEG_BIN = 'ffmpeg'

JAnimColor = Union[str, colour.Color, Iterable]

FLOAT_SIZE = ctypes.sizeof(ctypes.c_float)
UINT_SIZE = ctypes.sizeof(ctypes.c_uint)

ASPECT_RATIO = 16.0 / 9.0
FRAME_HEIGHT = 8.0
FRAME_WIDTH = FRAME_HEIGHT * ASPECT_RATIO
FRAME_Y_RADIUS = FRAME_HEIGHT / 2
FRAME_X_RADIUS = FRAME_WIDTH / 2

DEFAULT_PIXEL_HEIGHT = 1080
DEFAULT_PIXEL_WIDTH = 1920
DEFAULT_FRAME_RATE = 30

PIXEL_TO_FRAME_RATIO = FRAME_WIDTH / DEFAULT_PIXEL_WIDTH

DEFAULT_EPS = 1e-5

SMALL_BUFF = 0.1
MED_SMALL_BUFF = 0.25
MED_LARGE_BUFF = 0.5
LARGE_BUFF = 1

DEFAULT_ITEM_TO_EDGE_BUFF = MED_LARGE_BUFF
DEFAULT_ITEM_TO_ITEM_BUFF = MED_SMALL_BUFF

DEFAULT_RUN_TIME = 1.0
DEFAULT_WAIT_TIME = 1.0

ORIGIN = np.array((0., 0., 0.))
UP = np.array((0., 1., 0.))
DOWN = np.array((0., -1., 0.))
RIGHT = np.array((1., 0., 0.))
LEFT = np.array((-1., 0., 0.))
IN = np.array((0., 0., -1.))
OUT = np.array((0., 0., 1.))
X_AXIS = np.array((1., 0., 0.))
Y_AXIS = np.array((0., 1., 0.))
Z_AXIS = np.array((0., 0., 1.))

# Useful abbreviations for diagonals
UL = UP + LEFT
UR = UP + RIGHT
DL = DOWN + LEFT
DR = DOWN + RIGHT

TOP = FRAME_Y_RADIUS * UP
BOTTOM = FRAME_Y_RADIUS * DOWN
LEFT_SIDE = FRAME_X_RADIUS * LEFT
RIGHT_SIDE = FRAME_X_RADIUS * RIGHT

PI = np.pi
TAU = 2 * PI
DEGREES = TAU / 360
# Nice to have a constant for readability
# when juxtaposed with expressions like 30 * DEGREES
RADIANS = 1

# Related to Text
NORMAL = "NORMAL"
ITALIC = "ITALIC"
OBLIQUE = "OBLIQUE"
BOLD = "BOLD"
