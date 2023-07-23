import inspect

def safe_call(obj, method_name: str, default_ret=None, *args, **kwargs):
    if hasattr(obj, method_name):
        method = getattr(obj, method_name)
        if callable(method):
            return method(*args, **kwargs)
    return default_ret

def safe_call_same(obj, default_ret=None, *args, **kwargs):
    safe_call(obj, inspect.currentframe().f_back.f_code.co_name, default_ret, *args, **kwargs)

def get_proportional_scale_size(src_width, src_height, tg_width, tg_height):
    factor1 = tg_width / src_width
    factor2 = tg_height / src_height
    factor = min(factor1, factor2)
    return src_width * factor, src_height * factor

def decode_utf8(utf8: str) -> str:
    return bytes(utf8, encoding='utf-8').decode('utf-8')
