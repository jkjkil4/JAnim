import types


class Bind:
    def __init__(self, obj, instance, owner):
        self.obj = obj
        self.instance = instance
        self.owner = owner

    def __call__(self, *args, **kwargs):
        return types.MethodType(self.obj, self.instance)(*args, **kwargs)

    def __getattr__(self, method_name: str):
        return types.MethodType(getattr(self.obj, method_name), self.instance)
