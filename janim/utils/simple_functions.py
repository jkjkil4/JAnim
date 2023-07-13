import math
from functools import lru_cache

@lru_cache(maxsize=10)
def choose(n, k):
    return math.comb(n, k)