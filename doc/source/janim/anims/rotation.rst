.. _janim_anims_rotation:

rotation
========

.. important::

    如果你想要实现旋转效果，请不要尝试直接使用 ``self.play(item.anim.points.rotate(...))``，
    因为这只是在当前和结果之间进行 :class:`~.MethodTransform` ，并无旋转效果

    实现旋转效果请使用下方给出的 :class:`~.Rotate` 和 :class:`~.Rotating`

.. automodule:: janim.anims.rotation
    :members:
    :show-inheritance:

