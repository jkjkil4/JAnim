
def safe_call(obj, method_name: str, default_ret=None, *args, **kwargs):
    if hasattr(obj, method_name):
        method = getattr(obj, method_name)
        if callable(method):
            return method(*args, **kwargs)
    return default_ret