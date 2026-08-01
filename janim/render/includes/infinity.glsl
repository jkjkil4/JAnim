#ifdef COMPATIBILITY
const float INFINITY = 1.0 / 0.0;
#else
const float INFINITY = uintBitsToFloat(0x7F800000);
#endif
