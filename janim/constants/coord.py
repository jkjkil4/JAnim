import numpy as np

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

# TODO: Frame Coord
# TOP = FRAME_Y_RADIUS * UP
# BOTTOM = FRAME_Y_RADIUS * DOWN
# LEFT_SIDE = FRAME_X_RADIUS * LEFT
# RIGHT_SIDE = FRAME_X_RADIUS * RIGHT
