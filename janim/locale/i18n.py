import gettext
import locale
import os

from janim.utils.file_ops import get_janim_dir


lang: str | None = None


def set_lang(lang_code: str) -> None:
    global lang
    lang = lang_code


def get_lang() -> str:
    global lang
    if lang is not None:
        return lang
    return locale.getdefaultlocale()[0] or ''


def get_local_strings(domain: str):
    lang_code = get_lang()
    t = gettext.translation(domain,
                            os.path.join(get_janim_dir(), 'locale'),
                            languages=[lang_code],
                            fallback=True)
    return t.gettext
