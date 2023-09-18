

class Margins:
    '''
    定义了一组四个边距：左、上、右、下，用于描述矩形周围边框的大小。
    如果直接传入单个数值，则表示为四个方向皆为该值
    '''
    def __init__(self, buff: float | tuple[float]) -> None:
        self.buff = buff
        self.is_float = isinstance(buff, float)
    
    @property
    def left(self) -> float:
        return self.buff if self.is_float else self.buff[0]
    
    @property
    def top(self) -> float:
        return self.buff if self.is_float else self.buff[1]
    
    @property
    def right(self) -> float:
        return self.buff if self.is_float else self.buff[2]
    
    @property
    def bottom(self) -> float:
        return self.buff if self.is_float else self.buff[3]

MarginsType = Margins | float | tuple[float]
