from __future__ import annotations


# 兼容旧导入路径：
# `janim.items.frame_effect` 已拆分至 `janim.items.effect.*`
def __getattr__(name: str):
    if name in {'FrameEffect', 'simple_frameeffect_shader', 'SimpleFrameEffect'}:
        from janim.utils.deprecation import deprecated
        deprecated(
            f'janim.items.frame_effect.{name}',
            f'janim.items.effect.frame_effect.{name}',
            remove=(4, 4)
        )
        from janim.items.effect import frame_effect
        return getattr(frame_effect, name)

    if name in {
        'frameclip_fragment_shader',
        'Cmpt_FrameClip',
        'FrameClip',
        'transformable_frameclip_fragment_shader',
        'Cmpt_TransformableFrameClip',
        'TransformableFrameClip',
    }:
        from janim.utils.deprecation import deprecated
        deprecated(
            f'janim.items.frame_effect.{name}',
            f'janim.items.effect.clip.{name}',
            remove=(4, 4)
        )
        from janim.items.effect import clip
        return getattr(clip, name)

    if name in {'shadertoy_fragment_shader', 'Shadertoy', 'AlphaEffect'}:
        from janim.utils.deprecation import deprecated
        deprecated(
            f'janim.items.frame_effect.{name}',
            f'janim.items.effect.effects.{name}',
            remove=(4, 4)
        )
        from janim.items.effect import effects
        return getattr(effects, name)

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
