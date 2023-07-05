import ctypes

FLOAT_SIZE = ctypes.sizeof(ctypes.c_float)
UINT_SIZE = ctypes.sizeof(ctypes.c_uint)

IDEN_MAT = (
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1
)
