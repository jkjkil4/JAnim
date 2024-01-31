from dataclasses import dataclass


@dataclass
class AlignedData[T]:
    '''
    数据对齐后的结构，用于 :meth:`~.Item.Data.align_for_interpolate`
    '''
    data1: T
    data2: T
    union: T
