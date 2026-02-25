# flake8: noqa
# %% Imports
import os
import subprocess as sp
from io import BytesIO

import numpy as np
import svgelements as se

from janim.items.svg.svg_item import SVGItem
from janim.utils.bezier import PathBuilder

dir = os.path.dirname(__file__)

# %% Generate brace SVG using Typst
typst_src = '''
#set page(width: auto, height: auto, margin: 0pt, fill: none)

$ cases(#v(2.82em)) $
'''

command = [
    'typst',
    'compile',
    '-',    # input from stdin
    '-',    # output to stdout
    '--format', 'svg'
]

process = sp.Popen(command, stdin=sp.PIPE, stdout=sp.PIPE)
process.stdin.write(typst_src.encode('utf-8'))
process.stdin.close()
svg_output, _ = process.communicate()
if process.returncode != 0:
    raise RuntimeError(f'Typst compilation failed with return code {process.returncode}')

# %% Load SVG and break it into 3 pieces
svg: se.SVG = se.SVG.parse(BytesIO(svg_output))

paths = [
    elem
    for elem in svg.elements()
    if isinstance(elem, se.Path)
]

simplified_svg = se.SVG()
simplified_svg.extend(paths[::2])

# %% Write modified SVG into brace_parts.svg
xml = simplified_svg.string_xml()

with open(f'{dir}/brace_parts.svg', 'w') as f:
    f.write(xml)

# %% Load SVG by SVGItem, break 3 pieces (closed path) into 4 open paths
item = SVGItem(f'{dir}/brace_parts.svg', scale=24/11)
item.points.to_center()

points = item.points.get_all()
y = points[np.argmin(points[:, 0]), 1]
y_min = points[:, 1].min()
y_max = points[:, 1].max()

def point_fn(point):
    if np.isclose(point[1], y):
        res = 0
    elif point[1] > y:
        res = (point[1] - y) / (y_max - y) * y_max
    else:
        res = (point[1] - y) / (y_min - y) * y_min

    return [point[0], res, point[2]]

# Since the generated arm lengths are different, adjust them here to make them the same
item.points.apply_point_fn(point_fn)

def get_first_argmax_of_points(points: np.ndarray) -> int:
    idx = np.argmax(points[:, 1])
    for i in range(idx - 2, idx + 3):
        if np.isclose(points[i, 1], points[idx, 1]):
            return i

def get_first_argmin_of_points(points: np.ndarray) -> int:
    idx = np.argmin(points[:, 1])
    for i in range(idx - 2, idx + 3):
        if np.isclose(points[i, 1], points[idx, 1]):
            return i

points = item[0].points.get()
idx = get_first_argmax_of_points(points)
path1 = np.concatenate([points[idx + 2: -1], points[:idx + 1]])

points = item[2].points.get()
idx = get_first_argmin_of_points(points)
path3 = np.concatenate([points[idx + 2: -1], points[:idx + 1]])

points = item[1].points.get()
idx1 = get_first_argmax_of_points(points)
idx2 = get_first_argmin_of_points(points)
path2 = np.concatenate([points[idx2 + 2: -1], points[:idx1 + 1]])
path4 = points[idx1 + 2: idx2 + 1]

# %% Unique Brace
builder = PathBuilder(points=path1)
for path in (path2, path3, path4):
    builder.line_to(path[0])
    builder.append(path[1:])
builder.close_path()

points = builder.get().astype(np.float32)
np.save(f'{dir}/brace_unique.npy', points)

# %% Brace paths
np.save(f'{dir}/brace_path1.npy', path1.astype(np.float32))
np.save(f'{dir}/brace_path2.npy', path2.astype(np.float32))
np.save(f'{dir}/brace_path3.npy', path3.astype(np.float32))
np.save(f'{dir}/brace_path4.npy', path4.astype(np.float32))

# %% Cleanup
os.remove(f'{dir}/brace_parts.svg')
