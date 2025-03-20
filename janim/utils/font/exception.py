
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
    "Arial-Black":
        lambda: FontException(weight=900),
    # Fandol fonts designed for Chinese typesetting.
    # See https://ctan.org/tex-archive/fonts/fandol/.
    "FandolHei-Bold":
        lambda: FontException(weight=700),
    "FandolSong-Bold":
        lambda: FontException(weight=700),
    # Noto fonts
    "NotoNaskhArabicUISemi-Bold":
        lambda: FontException(weight=600),
    "NotoSansSoraSompengSemi-Bold":
        lambda: FontException(weight=600),
    # New Computer Modern
    "NewCM08-Book":
        lambda: FontException(weight=450),
    "NewCM08-BookItalic":
        lambda: FontException(weight=450),
    "NewCM10-Book":
        lambda: FontException(weight=450),
    "NewCM10-BookItalic":
        lambda: FontException(weight=450),
    "NewCMMath-Book":
        lambda: FontException(weight=450),
    "NewCMMono10-Book":
        lambda: FontException(weight=450),
    "NewCMMono10-BookItalic":
        lambda: FontException(weight=450),
    "NewCMSans08-Book":
        lambda: FontException(weight=450),
    "NewCMSans08-BookOblique":
        lambda: FontException(weight=450),
    "NewCMSans10-Book":
        lambda: FontException(weight=450),
    "NewCMSans10-BookOblique":
        lambda: FontException(weight=450, style=Style.Oblique),
    "NewCMSans10-Oblique":
        lambda: FontException(style=Style.Oblique),
    "NewCMUncial08-Book":
        lambda: FontException(weight=450),
    "NewCMUncial10-Book":
        lambda: FontException(weight=450),
    # Latin Modern
    "LMMonoLt10-BoldOblique":
        lambda: FontException(style=Style.Oblique),
    "LMMonoLt10-Regular":
        lambda: FontException(weight=300),
    "LMMonoLt10-Oblique":
        lambda: FontException(weight=300, style=Style.Oblique),
    "LMMonoLtCond10-Regular":
        lambda: FontException(weight=300, stretch=666),
    "LMMonoLtCond10-Oblique":
        lambda: FontException(weight=300, style=Style.Oblique, stretch=666),
    "LMMonoPropLt10-Regular":
        lambda: FontException(weight=300),
    "LMMonoPropLt10-Oblique":
        lambda: FontException(weight=300),
    # STKaiti is a set of Kai fonts. Their weight values need to be corrected
    # according to their PostScript names.
    "STKaitiSC-Regular":
        lambda: FontException(weight=400),
    "STKaitiTC-Regular":
        lambda: FontException(weight=400),
    "STKaitiSC-Bold":
        lambda: FontException(weight=700),
    "STKaitiTC-Bold":
        lambda: FontException(weight=700),
    "STKaitiSC-Black":
        lambda: FontException(weight=900),
    "STKaitiTC-Black":
        lambda: FontException(weight=900),
}
