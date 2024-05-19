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

NAN_POINT = np.full(3, np.nan)

# Useful abbreviations for diagonals
UL = UP + LEFT
UR = UP + RIGHT
DL = DOWN + LEFT
DR = DOWN + RIGHT

for p in (ORIGIN, UP, DOWN, RIGHT, LEFT, IN, OUT,
          X_AXIS, Y_AXIS, Z_AXIS, NAN_POINT,
          UL, UR, DL, DR):
    p.setflags(write=False)
