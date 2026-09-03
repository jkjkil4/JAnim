import glcontext
from janim_backend.ffi import Gl


def _load() -> Gl:
    backend = glcontext.default_backend()
    glctx = backend(
        glversion=330,
        mode='standalone',
    )
    return Gl.load(glctx.load)


gl = _load()
