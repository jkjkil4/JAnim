
from dataclasses import dataclass

from janim.utils.font.variant import Style


@dataclass
class FontException:
    family: str | None = None
    weight: int | None = None
    style: Style | None = None
    stretch: int | None = None


# 这个 EXCEPTION_MAP 虽然借鉴自 Typst，但是有一些差异
# 比如 "Archivo Narrow" 在 JAnim 中被正确处理，因此不需要那些对 family-name 的特判
# 所以，我把所有 family-name 的特判都删去了，如果有需要再说

# borrowed from https://github.com/typst/typst/blob/main/crates/typst-library/src/text/font/exceptions.rs
# A map which keys are PostScript name and values are override entries.
EXCEPTION_MAP = {
    # The old version of Arial-Black, published by Microsoft in 1996 in their
    # "core fonts for the web" project, has a wrong weight of 400.
    # See https://corefonts.sourceforge.net/.
    "Arial-Black": FontException(weight=900),
    # Fandol fonts designed for Chinese typesetting.
    # See https://ctan.org/tex-archive/fonts/fandol/.
    "FandolHei-Bold": FontException(weight=700),
    "FandolSong-Bold": FontException(weight=700),
    # Noto fonts
    "NotoNaskhArabicUISemi-Bold": FontException(weight=600),
    "NotoSansSoraSompengSemi-Bold": FontException(weight=600),
    # New Computer Modern
    "NewCM08-Book": FontException(weight=450),
    "NewCM08-BookItalic": FontException(weight=450),
    "NewCM10-Book": FontException(weight=450),
    "NewCM10-BookItalic": FontException(weight=450),
    "NewCMMath-Book": FontException(weight=450),
    "NewCMMono10-Book": FontException(weight=450),
    "NewCMMono10-BookItalic": FontException(weight=450),
    "NewCMSans08-Book": FontException(weight=450),
    "NewCMSans08-BookOblique": FontException(weight=450),
    "NewCMSans10-Book": FontException(weight=450),
    "NewCMSans10-BookOblique": FontException(weight=450, style=Style.Oblique),
    "NewCMSans10-Oblique": FontException(style=Style.Oblique),
    "NewCMUncial08-Book": FontException(weight=450),
    "NewCMUncial10-Book": FontException(weight=450),
    # Latin Modern
    "LMMonoLt10-BoldOblique": FontException(style=Style.Oblique),
    "LMMonoLt10-Regular": FontException(weight=300),
    "LMMonoLt10-Oblique": FontException(weight=300, style=Style.Oblique),
    "LMMonoLtCond10-Regular": FontException(weight=300, stretch=666),
    "LMMonoLtCond10-Oblique": FontException(weight=300, style=Style.Oblique, stretch=666),
    "LMMonoPropLt10-Regular": FontException(weight=300),
    "LMMonoPropLt10-Oblique": FontException(weight=300),
    # STKaiti is a set of Kai fonts. Their weight values need to be corrected
    # according to their PostScript names.
    "STKaitiSC-Regular": FontException(weight=400),
    "STKaitiTC-Regular": FontException(weight=400),
    "STKaitiSC-Bold": FontException(weight=700),
    "STKaitiTC-Bold": FontException(weight=700),
    "STKaitiSC-Black": FontException(weight=900),
    "STKaitiTC-Black": FontException(weight=900),
}
