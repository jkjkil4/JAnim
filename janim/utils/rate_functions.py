from janim.utils.bezier import bezier

from typing import Callable, Literal
import math
import numpy as np

type RateFunc = Callable[[float], float]


def linear(t: float) -> float:
    """
    线性插值

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 与输入相同的值
    :rtype: float
    """
    return t


def smooth(t: float) -> float:
    """
    平滑插值，在 t=0 和 t=1 处一阶和二阶导数为零

    等价于 ``bezier([0, 0, 0, 1, 1, 1])``

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 平滑插值后的值
    :rtype: float
    """
    s = 1 - t
    return (t**3) * (10 * s * s + 5 * s * t + t * t)


def rush_into(t: float) -> float:
    """
    快速进入效果，前半段使用 :func:`smooth` 加速

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 加速插值后的值
    :rtype: float
    """
    return 2 * smooth(0.5 * t)


def rush_from(t: float) -> float:
    """
    快速离开效果，后半段使用 :func:`smooth` 减速

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 减速插值后的值
    :rtype: float
    """
    return 2 * smooth(0.5 * (t + 1)) - 1


def slow_into(t: float) -> float:
    """
    缓慢进入效果，基于圆弧曲线减速到达终点

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 圆弧插值后的值
    :rtype: float
    """
    return np.sqrt(1 - (1 - t) * (1 - t))


def double_smooth(t: float) -> float:
    """
    双重平滑插值，前后半段各应用一次 :func:`smooth`

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 双重平滑插值后的值
    :rtype: float
    """
    if t < 0.5:
        return 0.5 * smooth(2 * t)
    else:
        return 0.5 * (1 + smooth(2 * t - 1))


def there_and_back(t: float) -> float:
    """
    往返效果，从 0 平滑到 1 再平滑回 0

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 往返插值后的值
    :rtype: float
    """
    new_t = 2 * t if t < 0.5 else 2 * (1 - t)
    return smooth(new_t)


def there_and_back_with_pause(t: float, pause_ratio: float = 1. / 3) -> float:
    """
    带停顿的往返效果，在峰值处保持一段时间后返回

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param pause_ratio: 在峰值处停顿的时间比例
    :type pause_ratio: float
    :return: 带停顿的往返插值后的值
    :rtype: float
    """
    a = 2. / (1. - pause_ratio)
    if t < 0.5 - pause_ratio / 2:
        return smooth(a * t)
    elif t < 0.5 + pause_ratio / 2:
        return 1
    else:
        return smooth(a - a * t)

def make_there_and_back_with_pause(pause_ratio: float = 1. / 3) -> RateFunc:
    """
    创建指定停顿比例的 :func:`there_and_back_with_pause` 速率函数

    :param pause_ratio: 在峰值处停顿的时间比例
    :type pause_ratio: float
    :return: 速率函数
    :rtype: RateFunc
    """
    return lambda t: there_and_back_with_pause(t, pause_ratio)


def running_start(t: float, pull_factor: float = -0.5) -> float:
    """
    助跑效果，先向反方向拉伸再冲向终点

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param pull_factor: 反向拉伸的程度，负值表示反向
    :type pull_factor: float
    :return: 助跑插值后的值
    :rtype: float
    """
    return bezier([0, 0, pull_factor, pull_factor, 1, 1, 1])(t)

def make_running_start(pull_factor: float = -0.5) -> RateFunc:
    """
    创建指定拉伸程度的 :func:`running_start` 速率函数

    :param pull_factor: 反向拉伸的程度，负值表示反向
    :type pull_factor: float
    :return: 速率函数
    :rtype: RateFunc
    """
    return lambda t: running_start(t, pull_factor)


def not_quite_there(
    func: RateFunc = smooth,
    proportion: float = 0.7
) -> RateFunc:
    """
    创建一个不完全到达终点的速率函数

    :param func: 基础速率函数
    :type func: RateFunc
    :param proportion: 最终到达的比例，默认 0.7 即只到达 70%
    :type proportion: float
    :return: 缩放后的速率函数
    :rtype: RateFunc
    """
    def result(t):
        return proportion * func(t)
    return result


def wiggle(t: float, wiggles: float = 2) -> float:
    """
    摆动效果，在往返过程中叠加正弦振荡

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param wiggles: 振荡次数
    :type wiggles: float
    :return: 摆动插值后的值
    :rtype: float
    """
    return there_and_back(t) * np.sin(wiggles * np.pi * t)

def make_wiggle(wiggles: float = 2) -> RateFunc:
    """
    创建指定振荡次数的 :func:`wiggle` 速率函数

    :param wiggles: 振荡次数
    :type wiggles: float
    :return: 速率函数
    :rtype: RateFunc
    """
    return lambda t: wiggle(t, wiggles)


def squish_rate_func(
    func: RateFunc,
    a: float = 0.4,
    b: float = 0.6
) -> RateFunc:
    """
    将速率函数压缩到 [a, b] 区间内执行，区间外返回端点值

    :param func: 基础速率函数
    :type func: RateFunc
    :param a: 压缩区间的起点
    :type a: float
    :param b: 压缩区间的终点
    :type b: float
    :return: 压缩后的速率函数
    :rtype: RateFunc
    """
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
    """
    在 [0, 1] 区间内使用给定速率函数，区间外使用线性插值

    :param func: 基础速率函数
    :type func: RateFunc
    :return: 区间外线性扩展的速率函数
    :rtype: RateFunc
    """
    def result(t):
        if 0 <= t <= 1:
            return func(t)
        return t

    return result


def lingering(t: float) -> float:
    """
    延迟效果，在 [0, 0.8] 区间内线性到达终点后保持不变

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 延迟插值后的值
    :rtype: float
    """
    return squish_rate_func(lambda t: t, 0, 0.8)(t)


def exponential_decay(t: float, half_life: float = 0.1) -> float:
    """
    指数衰减效果，快速接近终点后趋于平稳

    半衰期应设置较小的值以减少末端的截断误差

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param half_life: 半衰期，值越小衰减越快
    :type half_life: float
    :return: 指数衰减插值后的值
    :rtype: float
    """
    return 1 - np.exp(-t / half_life)

def make_exponential_decay(half_life: float = 0.1) -> RateFunc:
    """
    创建指定半衰期的 :func:`exponential_decay` 速率函数

    :param half_life: 半衰期，值越小衰减越快
    :type half_life: float
    :return: 速率函数
    :rtype: RateFunc
    """
    return lambda t: exponential_decay(t, half_life)


ELASTIC_CONST = 2 * math.pi / .3
ELASTIC_CONST2 = .3 / 4

BACK_CONST = 1.70158
BACK_CONST2 = BACK_CONST * 1.525

BOUNCE_CONST = 1 / 2.75

# 用于修正指数和弹性曲线使其在 0/1 处起止的偏移常量
EXPO_OFFSET = 2**(-10)
ELASTIC_OFFSET_FULL = 2**(-11)
ELASTIC_OFFSET_HALF = 2**(-10) * math.sin((.5 - ELASTIC_CONST2) * ELASTIC_CONST)
ELASTIC_OFFSET_QUARTER = 2**(-10) * math.sin((.25 - ELASTIC_CONST2) * ELASTIC_CONST)
IN_OUT_ELASTIC_OFFSET = 2**(-10) * math.sin((1 - ELASTIC_CONST2 * 1.5) * ELASTIC_CONST / 1.5)


def ease_in_quad(t: float) -> float:
    """
    二次方缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 二次方缓入插值后的值
    :rtype: float
    """
    return t**2


def ease_out_quad(t: float) -> float:
    """
    二次方缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 二次方缓出插值后的值
    :rtype: float
    """
    return t * (2 - t)


def ease_inout_quad(t: float) -> float:
    """
    二次方缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 二次方缓入缓出插值后的值
    :rtype: float
    """
    return (
        t**2 * 2
        if t < .5
        else (t - 1)**2 * -2 + 1
    )


def ease_in_cubic(t: float) -> float:
    """
    三次方缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 三次方缓入插值后的值
    :rtype: float
    """
    return t**3


def ease_out_cubic(t: float) -> float:
    """
    三次方缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 三次方缓出插值后的值
    :rtype: float
    """
    return (t - 1)**3 + 1


def ease_inout_cubic(t: float) -> float:
    """
    三次方缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 三次方缓入缓出插值后的值
    :rtype: float
    """
    return (
        t**3 * 4
        if t < .5
        else (t - 1)**3 * 4 + 1
    )


def ease_in_quart(t: float) -> float:
    """
    四次方缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 四次方缓入插值后的值
    :rtype: float
    """
    return t**4


def ease_out_quart(t: float) -> float:
    """
    四次方缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 四次方缓出插值后的值
    :rtype: float
    """
    return 1 - (t - 1)**4


def ease_inout_quart(t: float) -> float:
    """
    四次方缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 四次方缓入缓出插值后的值
    :rtype: float
    """
    return (
        t**4 * 8
        if t < .5
        else (t - 1)**4 * -8 + 1
    )


def ease_in_quint(t: float) -> float:
    """
    五次方缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 五次方缓入插值后的值
    :rtype: float
    """
    return t**5


def ease_out_quint(t: float) -> float:
    """
    五次方缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 五次方缓出插值后的值
    :rtype: float
    """
    return (t - 1)**5 + 1


def ease_inout_quint(t: float) -> float:
    """
    五次方缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 五次方缓入缓出插值后的值
    :rtype: float
    """
    return (
        t**5 * 16
        if t < .5
        else (t - 1)**5 * 16 + 1
    )


def ease_in_sine(t: float) -> float:
    """
    正弦缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 正弦缓入插值后的值
    :rtype: float
    """
    return 1 - math.cos(t * math.pi * .5)


def ease_out_sine(t: float) -> float:
    """
    正弦缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 正弦缓出插值后的值
    :rtype: float
    """
    return math.sin(t * math.pi * .5)


def ease_inout_sine(t: float) -> float:
    """
    正弦缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 正弦缓入缓出插值后的值
    :rtype: float
    """
    return .5 - .5 * math.cos(math.pi * t)


def ease_in_expo(t: float) -> float:
    """
    指数缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 指数缓入插值后的值
    :rtype: float
    """
    return 2**(10 * (t - 1)) + EXPO_OFFSET * (t - 1)


def ease_out_expo(t: float) -> float:
    """
    指数缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 指数缓出插值后的值
    :rtype: float
    """
    return -(2**(-10 * t)) + 1 + EXPO_OFFSET * t


def ease_inout_expo(t: float) -> float:
    """
    指数缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 指数缓入缓出插值后的值
    :rtype: float
    """
    return (
        .5 * 2**(20 * t - 10) + EXPO_OFFSET * (2 * t - 1)
        if t < .5
        else 1 - .5 * 2**(-20 * t + 10) + EXPO_OFFSET * (-2 * t + 1)
    )


def ease_in_circ(t: float) -> float:
    """
    圆弧缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 圆弧缓入插值后的值
    :rtype: float
    """
    return 1 - math.sqrt(1 - t**2)


def ease_out_circ(t: float) -> float:
    """
    圆弧缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 圆弧缓出插值后的值
    :rtype: float
    """
    return math.sqrt(1 - (t - 1)**2)


def ease_inout_circ(t: float) -> float:
    """
    圆弧缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 圆弧缓入缓出插值后的值
    :rtype: float
    """
    t *= 2
    return (
        .5 - .5 * math.sqrt(1 - t**2)
        if t < 1
        else .5 * math.sqrt(1 - (t - 2)**2) + .5
    )


def ease_in_elastic(t: float) -> float:
    """
    弹性缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹性缓入插值后的值
    :rtype: float
    """
    return -(2**(-10 + 10 * t)) * math.sin((1 - ELASTIC_CONST2 - t) * ELASTIC_CONST) \
        + ELASTIC_OFFSET_FULL * (1 - t)


def ease_out_elastic(t: float) -> float:
    """
    弹性缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹性缓出插值后的值
    :rtype: float
    """
    return 2**(-10 * t) * math.sin((t - ELASTIC_CONST2) * ELASTIC_CONST) \
        + 1 - ELASTIC_OFFSET_FULL * t


def ease_out_elastic_half(t: float) -> float:
    """
    弹性缓出（半振幅）

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹性缓出（半振幅）插值后的值
    :rtype: float
    """
    return 2**(-10 * t) * math.sin((.5 * t - ELASTIC_CONST2) * ELASTIC_CONST) \
        + 1 - ELASTIC_OFFSET_HALF * t


def ease_out_elastic_quarter(t: float) -> float:
    """
    弹性缓出（四分之一振幅）

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹性缓出（四分之一振幅）插值后的值
    :rtype: float
    """
    return 2**(-10 * t) * math.sin((.25 * t - ELASTIC_CONST2) * ELASTIC_CONST) \
        + 1 - ELASTIC_OFFSET_QUARTER * t


def ease_inout_elastic(t: float) -> float:
    """
    弹性缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹性缓入缓出插值后的值
    :rtype: float
    """
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
    """
    回弹缓入，起始时略微反向运动

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 回弹缓入插值后的值
    :rtype: float
    """
    return t**2 * ((BACK_CONST + 1) * t - BACK_CONST)


def ease_out_back(t: float) -> float:
    """
    回弹缓出，到达终点时略微超出后回弹

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 回弹缓出插值后的值
    :rtype: float
    """
    return (t - 1)**2 * ((BACK_CONST + 1) * (t - 1) + BACK_CONST) + 1


def ease_inout_back(t: float) -> float:
    """
    回弹缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 回弹缓入缓出插值后的值
    :rtype: float
    """
    t *= 2
    if t < 1:
        return .5 * t**2 * ((BACK_CONST2 + 1) * t - BACK_CONST2)
    t -= 2
    return .5 * (t**2 * ((BACK_CONST2 + 1) * t + BACK_CONST2) + 2)


def ease_in_bounce(t: float) -> float:
    """
    弹跳缓入

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹跳缓入插值后的值
    :rtype: float
    """
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
    """
    弹跳缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹跳缓出插值后的值
    :rtype: float
    """
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
    """
    弹跳缓入缓出

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 弹跳缓入缓出插值后的值
    :rtype: float
    """
    return (
        .5 - .5 * ease_out_bounce(1 - t * 2)
        if t < .5
        else ease_out_bounce((t - .5) * 2) * .5 + .5
    )


def spring(t: float, damping: float = 0.4, oscillations: float = 3.0) -> float:
    """
    弹簧效果，到达终点后产生阻尼振荡

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param damping: 阻尼系数，值越大振荡衰减越快
    :type damping: float
    :param oscillations: 振荡次数
    :type oscillations: float
    :return: 弹簧插值后的值
    :rtype: float
    """
    if t == 0.0 or t == 1.0:
        return t

    freq = oscillations * 2 * math.pi
    decay = np.exp(-t * 10 * damping)
    return 1 - decay * np.cos(t * freq)

def make_spring(damping: float = 0.4, oscillations: float = 3.0) -> RateFunc:
    """
    创建指定参数的 :func:`spring` 速率函数

    :param damping: 阻尼系数，值越大振荡衰减越快
    :type damping: float
    :param oscillations: 振荡次数
    :type oscillations: float
    :return: 速率函数
    :rtype: RateFunc
    """
    def result(t: float) -> float:
        return spring(t, damping, oscillations)
    return result


def steps(t: float, step_count: int = 5, step_position: Literal["start", "end"] = "end") -> float:
    """
    阶梯效果，将连续变化离散为若干等分台阶

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param step_count: 台阶数量
    :type step_count: int
    :param step_position: 台阶取值位置，``"start"`` 为向上取整，``"end"`` 为向下取整
    :type step_position: Literal["start", "end"]
    :return: 阶梯插值后的值
    :rtype: float
    """
    if step_position == "start":
        return math.ceil(t * step_count) / step_count
    else:
        if t == 1.0: return 1.0
        return math.floor(t * step_count) / step_count

def make_steps(step_count: int = 5, step_position: Literal["start", "end"] = "end") -> RateFunc:
    """
    创建指定参数的 :func:`steps` 速率函数

    :param step_count: 台阶数量
    :type step_count: int
    :param step_position: 台阶取值位置，``"start"`` 为向上取整，``"end"`` 为向下取整
    :type step_position: Literal["start", "end"]
    :return: 速率函数
    :rtype: RateFunc
    """
    return lambda t: steps(t, step_count, step_position)


def pulse(t: float, pulses: int = 2) -> float:
    """
    脉冲效果，产生正弦平方波形的周期性脉冲

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :param pulses: 脉冲次数
    :type pulses: int
    :return: 脉冲插值后的值
    :rtype: float
    """
    return math.sin(t * pulses * math.pi) ** 2

def make_pulse(pulses: int = 2) -> RateFunc:
    """
    创建指定脉冲次数的 :func:`pulse` 速率函数

    :param pulses: 脉冲次数
    :type pulses: int
    :return: 速率函数
    :rtype: RateFunc
    """
    return lambda t: pulse(t, pulses)


def slow_mid(t: float) -> float:
    """
    中段减速效果，两端快中间慢的三次方曲线

    :param t: 时间参数，范围 [0, 1]
    :type t: float
    :return: 中段减速插值后的值
    :rtype: float
    """
    if t == 0.5:
        return 0.5
    return 4 * (t - 0.5)**3 + 0.5
