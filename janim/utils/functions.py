
def safe_call(obj, method_name: str, default_ret=None, *args, **kwargs):
    if hasattr(obj, method_name):
        method = getattr(obj, method_name)
        if callable(method):
            return method(*args, **kwargs)
    return default_ret

def get_proportional_scale_size(src_width, src_height, tg_width, tg_height):
    factor1 = tg_width / src_width
    factor2 = tg_height / src_height
    factor = min(factor1, factor2)
    return src_width * factor, src_height * factor
