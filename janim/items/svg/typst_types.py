from typing import Iterable, Literal

from janim.items.points import Points
from janim.items.svg.typst import TypstText

type TypMatDelim = Literal['(', ')', '[', ']', '{', '}', '|']
type TypAlignment = Literal['start', 'end', 'left', 'center', 'right', 'top', 'horizon', 'bottom']
type TypMatAlignment = Literal['start', 'left', 'center', 'right', 'end']   # 矩阵不支持 'top', 'horizon', 'bottom'

typst_matrix_template = '''
#set math.mat(
{typst_args_str}
)

$ mat(
{typst_str}
) $
'''


class TypstMatrix(TypstText):
    '''
    使用 Typst 进行矩阵布局

    传参请参考 Typst 文档 https://typst.app/docs/reference/math/mat/ ，以下给出部分示例

    .. code-block:: python

        TypstMatrix(
            [
                [1, 2, 3],
                [4, Arrow(ORIGIN, RIGHT), 6],
                [7, 8, 9]
            ],
        ).show()

    .. code-block:: python

        TypstMatrix(
            [
                [1, 2, 3],
                [4, Arrow(ORIGIN, RIGHT), 6],
                [7, 8, 9]
            ],
            gap='2em',
        ).show()

    .. code-block:: python

        TypstMatrix(
            [
                [1, 2, 3],
                [4, Arrow(ORIGIN, RIGHT), 6],
                [7, 8, 9]
            ],
            delim='[',
            align='right',
            augment=2,
            gap='0.5em',
        )

    .. code-block:: python

        TypstMatrix(
            [
                [1, 2, 3],
                [4, Circle(radius=0.25, fill_alpha=0.5), 6],
                [7, 8, 9]
            ],
            delim='[',
            augment=2,
            column_gap='0.7em',
            preamble='#set text(size: 3em)'
        ).show()
    '''

    def __init__(
        self,
        matrix: Iterable[Iterable[str | float | Points]],
        delim: str | TypMatDelim | tuple[TypMatDelim, TypMatDelim] | None = None,
        align: TypMatAlignment | None = None,
        augment: int | str | None = None,
        gap: str | None = None,
        row_gap: str | None = None,
        column_gap: str | None = None,
        **kwargs
    ):
        typst_args = {}

        if delim is not None:
            if isinstance(delim, str):
                if delim in '()[]{}':
                    delim = f'"{delim}"'
                typst_args['delim'] = delim
            else:
                typst_args['delim'] = f'({delim[0]}, {delim[1]})'
        if align is not None:
            typst_args['align'] = align
        if augment is not None:
            typst_args['augment'] = augment
        if gap is not None:
            typst_args['gap'] = gap
        if row_gap is not None:
            typst_args['row-gap'] = row_gap
        if column_gap is not None:
            typst_args['column-gap'] = column_gap

        vars = {}

        def register(item: Points) -> str:
            name = f'mat_{len(vars)}'
            vars[name] = item
            return name

        converted = [
            [
                f'#move(box({register(item)}))' if isinstance(item, Points) else str(item)
                for item in row
            ]
            for row in matrix
        ]

        typst_str = ' ;\n'.join(
            ', '.join(row)
            for row in converted
        )
        typst_args_str = ',\n'.join(f'{key}: {value}' for key, value in typst_args.items())

        super().__init__(
            typst_matrix_template.format(
                typst_args_str=typst_args_str,
                typst_str=typst_str
            ),
            vars=vars,
            **kwargs
        )
