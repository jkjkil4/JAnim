from enum import StrEnum
from typing import Literal


class Weight(StrEnum):
    Thin = 'thin'
    ExtraLight = 'extralight'
    Light = 'light'
    Regular = 'regular'
    Normal = 'normal'
    Medium = 'medium'
    SemiBold = 'semibold'
    Bold = 'bold'
    ExtraBold = 'extrabold'
    Black = 'black'


class Style(StrEnum):
    Normal = 'normal'
    Italic = 'italic'
    Oblique = 'oblique'


type WeightName = Literal['thin', 'extralight', 'light', 'regular', 'normal',
                          'medium', 'semibold', 'bold', 'extrabold', 'black']
type StyleName = Literal['normal', 'italic', 'oblique']

WEIGHT_MAP = {
    Weight.Thin: 100,
    Weight.ExtraLight: 200,
    Weight.Light: 300,
    Weight.Regular: 400,
    Weight.Normal: 400,
    Weight.Medium: 500,
    Weight.SemiBold: 600,
    Weight.Bold: 700,
    Weight.ExtraBold: 800,
    Weight.Black: 900,
}
