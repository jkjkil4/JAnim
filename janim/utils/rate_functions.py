import math
from typing import Callable

import numpy as np

from janim.utils.bezier import bezier

type RateFunc = Callable[[float], float]


def linear(t: float) -> float:
    return t


def smooth(t: float) -> float:
    # Zero first and second derivatives at t=0 and t=1.
    # Equivalent to bezier([0, 0, 0, 1, 1, 1])
    s = 1 - t
    return (t**3) * (10 * s * s + 5 * s * t + t * t)


def rush_into(t: float) -> float:
    return 2 * smooth(0.5 * t)


def rush_from(t: float) -> float:
    return 2 * smooth(0.5 * (t + 1)) - 1


def slow_into(t: float) -> float:
    return np.sqrt(1 - (1 - t) * (1 - t))


def double_smooth(t: float) -> float:
    if t < 0.5:
        return 0.5 * smooth(2 * t)
    else:
        return 0.5 * (1 + smooth(2 * t - 1))


def there_and_back(t: float) -> float:
    new_t = 2 * t if t < 0.5 else 2 * (1 - t)
    return smooth(new_t)


def there_and_back_with_pause(t: float, pause_ratio: float = 1. / 3) -> float:
    a = 2. / (1. - pause_ratio)
    if t < 0.5 - pause_ratio / 2:
        return smooth(a * t)
    elif t < 0.5 + pause_ratio / 2:
        return 1
    else:
        return smooth(a - a * t)


def running_start(t: float, pull_factor: float = -0.5) -> float:
    return bezier([0, 0, pull_factor, pull_factor, 1, 1, 1])(t)


def not_quite_there(
    func: RateFunc = smooth,
    proportion: float = 0.7
) -> RateFunc:
    def result(t):
        return proportion * func(t)
    return result


def wiggle(t: float, wiggles: float = 2) -> float:
    return there_and_back(t) * np.sin(wiggles * np.pi * t)


def squish_rate_func(
    func: RateFunc,
    a: float = 0.4,
    b: float = 0.6
) -> RateFunc:
    def result(t):
        if a == b:
            return a
        elif t < a:
            return func(0)
        elif t > b:
            return func(1)
        else:
            return func((t - a) / (b - a))

    return result


def outside_linear_rate_func(func: RateFunc) -> RateFunc:
    def result(t):
        if 0 <= t <= 1:
            return func(t)
        return t

    return result

# Stylistically, should this take parameters (with default values)?
# Ultimately, the functionality is entirely subsumed by squish_rate_func,
# but it may be useful to have a nice name for with nice default params for
# "lingering", different from squish_rate_func's default params


def lingering(t: float) -> float:
    return squish_rate_func(lambda t: t, 0, 0.8)(t)


def exponential_decay(t: float, half_life: float = 0.1) -> float:
    # The half-life should be rather small to minimize
    # the cut-off error at the end
    return 1 - np.exp(-t / half_life)


ELASTIC_CONST = 2 * math.pi / .3
ELASTIC_CONST2 = .3 / 4

BACK_CONST = 1.70158
BACK_CONST2 = BACK_CONST * 1.525

BOUNCE_CONST = 1 / 2.75

# constants used to fix expo and elastic curves to start/end at 0/1
EXPO_OFFSET = 2**(-10)
ELASTIC_OFFSET_FULL = 2**(-11)
ELASTIC_OFFSET_HALF = 2**(-10) * math.sin((.5 - ELASTIC_CONST2) * ELASTIC_CONST)
ELASTIC_OFFSET_QUARTER = 2**(-10) * math.sin((.25 - ELASTIC_CONST2) * ELASTIC_CONST)
IN_OUT_ELASTIC_OFFSET = 2**(-10) * math.sin((1 - ELASTIC_CONST2 * 1.5) * ELASTIC_CONST / 1.5)


def ease_in_quad(t: float) -> float:
    return t**2


def ease_out_quad(t: float) -> float:
    return t * (2 - t)


def ease_inout_quad(t: float) -> float:
    return (
        t**2 * 2
        if t < .5
        else (t - 1)**2 * -2 + 1
    )


def ease_in_cubic(t: float) -> float:
    return t**3


def ease_out_cubic(t: float) -> float:
    return (t - 1)**3 + 1


def ease_inout_cubic(t: float) -> float:
    return (
        t**3 * 4
        if t < .5
        else (t - 1)**3 * 4 + 1
    )


def ease_in_quart(t: float) -> float:
    return t**4


def ease_out_quart(t: float) -> float:
    return 1 - (t - 1)**4


def ease_inout_quart(t: float) -> float:
    return (
        t**4 * 8
        if t < .5
        else (t - 1)**4 * -8 + 1
    )


def ease_in_quint(t: float) -> float:
    return t**5


def ease_out_quint(t: float) -> float:
    return (t - 1)**5 + 1


def ease_inout_quint(t: float) -> float:
    return (
        t**5 * 16
        if t < .5
        else (t - 1)**5 * 16 + 1
    )


def ease_in_sine(t: float) -> float:
    return 1 - math.cos(t * math.pi * .5)


def ease_out_sine(t: float) -> float:
    return math.sin(t * math.pi * .5)


def ease_inout_sine(t: float) -> float:
    return .5 - .5 * math.cos(math.pi * t)


def ease_in_expo(t: float) -> float:
    return 2**(10 * (t - 1)) + EXPO_OFFSET * (t - 1)


def ease_out_expo(t: float) -> float:
    return -(2**(-10 * t)) + 1 + EXPO_OFFSET * t


def ease_inout_expo(t: float) -> float:
    return (
        .5 * 2**(20 * t - 10) + EXPO_OFFSET * (2 * t - 1)
        if t < .5
        else 1 - .5 * 2**(-20 * t + 10) + EXPO_OFFSET * (-2 * t + 1)
    )


def ease_in_circ(t: float) -> float:
    return 1 - math.sqrt(1 - t**2)


def ease_out_circ(t: float) -> float:
    return math.sqrt(1 - (t - 1)**2)


def ease_inout_circ(t: float) -> float:
    t *= 2
    return (
        .5 - .5 * math.sqrt(1 - t**2)
        if t < 1
        else .5 * math.sqrt(1 - (t - 2)**2) + .5
    )


def ease_in_elastic(t: float) -> float:
    return -(2**(-10 + 10 * t)) * math.sin((1 - ELASTIC_CONST2 - t) * ELASTIC_CONST) \
        + ELASTIC_OFFSET_FULL * (1 - t)


def ease_out_elastic(t: float) -> float:
    return 2**(-10 * t) * math.sin((t - ELASTIC_CONST2) * ELASTIC_CONST) \
        + 1 - ELASTIC_OFFSET_FULL * t


def ease_out_elastic_half(t: float) -> float:
    return 2**(-10 * t) * math.sin((.5 * t - ELASTIC_CONST2) * ELASTIC_CONST) \
        + 1 - ELASTIC_OFFSET_HALF * t


def ease_out_elastic_quarter(t: float) -> float:
    return 2**(-10 * t) * math.sin((.25 * t - ELASTIC_CONST2) * ELASTIC_CONST) \
        + 1 - ELASTIC_OFFSET_QUARTER * t


def ease_inout_elastic(t: float) -> float:
    t *= 2
    if t < 1:
        return -.5 * (
            2**(-10 + 10 * t) * math.sin((1 - ELASTIC_CONST2 * 1.5 - t) * ELASTIC_CONST / 1.5)
            - IN_OUT_ELASTIC_OFFSET * (1 - t)
        )
    t -= 1
    return .5 * (
        2**(-10 * t) * math.sin((t - ELASTIC_CONST2 * 1.5) * ELASTIC_CONST / 1.5)
        - IN_OUT_ELASTIC_OFFSET * t
    ) + 1


def ease_in_back(t: float) -> float:
    return t**2 * ((BACK_CONST + 1) * t - BACK_CONST)


def ease_out_back(t: float) -> float:
    return (t - 1)**2 * ((BACK_CONST + 1) * (t - 1) + BACK_CONST) + 1


def ease_inout_back(t: float) -> float:
    t *= 2
    if t < 1:
        return .5 * t**2 * ((BACK_CONST2 + 1) * t - BACK_CONST2)
    t -= 2
    return .5 * (t**2 * ((BACK_CONST2 + 1) * t + BACK_CONST2) + 2)


def ease_in_bounce(t: float) -> float:
    t = 1 - t
    if t < BOUNCE_CONST:
        return 1 - 7.5625 * t**2
    if t < 2 * BOUNCE_CONST:
        t -= 1.5 * BOUNCE_CONST
        return 1 - (7.5625 * t**2 + .75)
    if t < 2.5 * BOUNCE_CONST:
        t -= 2.25 * BOUNCE_CONST
        return 1 - (7.5625 * t**2 + .9375)
    t -= 2.625 * BOUNCE_CONST
    return 1 - (7.5625 * t**2 + .984375)


def ease_out_bounce(t: float) -> float:
    if t < BOUNCE_CONST:
        return 7.5625 * t**2
    if t < 2 * BOUNCE_CONST:
        t -= 1.5 * BOUNCE_CONST
        return 7.5625 * t**2 + .75
    if t < 2.5 * BOUNCE_CONST:
        t -= 2.25 * BOUNCE_CONST
        return 7.5625 * t**2 + .9375
    t -= 2.625 * BOUNCE_CONST
    return 7.5625 * t**2 + .984375


def ease_inout_bounce(t: float) -> float:
    return (
        .5 - .5 * ease_out_bounce(1 - t * 2)
        if t < .5
        else ease_out_bounce((t - .5) * 2) * .5 + .5
    )
