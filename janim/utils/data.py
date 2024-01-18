from dataclasses import dataclass


@dataclass
class AlignedData[T]:
    data1: T
    data2: T
    union: T
