from typing import Any, Iterable, Literal, NoReturn

from janim.exception import InvalidOrdinalError
from janim.items.points import Group, Points
from janim.items.svg.svg_item import SVGElemItem
from janim.items.svg.typst import TypstText
from janim.locale.i18n import get_local_strings

type TypMatDelim = Literal['(', ')', '[', ']', '{', '}', '|', 'none']
type TypAlignment = Literal['start', 'end', 'left', 'center', 'right', 'top', 'horizon', 'bottom']
type TypMatAlignment = Literal['start', 'left', 'center', 'right', 'end']   # 矩阵不支持 'top', 'horizon', 'bottom'

_ = get_local_strings('typst_types')

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

    - 使用 :meth:`get_inserted` 得到插入的 JAnim 物件
    - 使用 :meth:`get_element` 根据行列得到元素（需要传入 ``label=True`` 启用）

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
        *,
        align: TypMatAlignment | None = None,
        augment: int | str | None = None,
        gap: str | None = None,
        row_gap: str | None = None,
        column_gap: str | None = None,
        label: bool = False,
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

        def register(item: Points | Any) -> str:
            name = f'mat_{len(vars)}'
            vars[name] = item
            return name

        if not label:
            converted = [
                [
                    f'#move(box({register(item)}))' if isinstance(item, Points) else str(item)
                    for item in row_items
                ]
                for row_items in matrix
            ]
        else:
            self.matrix_label_mapping: dict[str, str] = {}
            matrix_labels: list[str] = []

            def register_matrix_label(item: Points | Any, row: int, col: int) -> str:
                matrix_label = f'__ja__mat_{row}_{col}'
                matrix_labels.append(matrix_label)
                if isinstance(item, Points):
                    name = register(item)
                    self.matrix_label_mapping[matrix_label] = f'__ja__{name}'
                    return f'#move(box({name}))'
                return f'#move[#box[{str(item)}] <{matrix_label}>]'

            converted = [
                [
                    register_matrix_label(item, row, col)
                    for col, item in enumerate(row_items)
                ]
                for row, row_items in enumerate(matrix)
            ]

        self.registered_count = len(vars)
        self.labelled = label

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

        if label:
            # 把 matrix_labels 没出现在 self.groups 的剔除掉
            # 并按照在 self.groups 中出现的顺序排序
            order = {key: i for i, key in enumerate(self.groups.keys())}
            order.update({
                mapfrom: order[mapto]
                for mapfrom, mapto in self.matrix_label_mapping.items()
            })
            self.matrix_labels = sorted(
                filter(
                    lambda matrix_coord: matrix_coord in self.groups or matrix_coord in self.matrix_label_mapping,
                    matrix_labels
                ),
                key=lambda matrix_coord: order[matrix_coord]
            )
            '''
            按照子物件顺序排列的矩阵元素标签
            '''

    def get_inserted(self, index: int) -> Points:
        '''
        获取插入的第 ``index`` 个 JAnim 物件

        ``index`` 从 0 开始计数
        '''
        if not 0 <= index < self.registered_count:
            raise InvalidOrdinalError(
                _('Index out of range, only {count} inserted items available')
                .format(count=self.registered_count)
            )
        return self.groups[f'__ja__mat_{index}'][0]

    def _get_element(self, matrix_label: str) -> Group[SVGElemItem] | Points | None:
        lst = self.groups.get(matrix_label, None)
        if lst is not None:
            return Group.from_iterable(lst)

        label = self.matrix_label_mapping.get(matrix_label, None)
        if label is not None:
            return Group.from_iterable(self.groups[label])[0]

        return None

    def get_element(self, row: int, col: int) -> Group[SVGElemItem] | Points:
        '''
        根据行列索引元素

        需要在构造 :class:`TypstMatrix` 时传入 ``label=True`` 启用
        '''
        self._raise_if_not_labelled()

        element = self._get_element(f'__ja__mat_{row}_{col}')
        if element is None:
            raise InvalidOrdinalError(
                _('Element not found in matrix at position ({row}, {col})')
                .format(row=row, col=col)
            )

        return element

    def get_elements(self) -> list[Group[SVGElemItem] | Points]:
        '''
        获取矩阵中所有元素

        需要在构造 :class:`TypstMatrix` 时传入 ``label=True`` 启用
        '''
        self._raise_if_not_labelled()

        return [
            self._get_element(matrix_label)
            for matrix_label in self.matrix_labels
        ]

    def get_left_brace(self) -> Group[SVGElemItem]:
        '''
        获取左大括号元素

        需要在构造 :class:`TypstMatrix` 时传入 ``label=True`` 启用
        '''
        self._raise_if_not_labelled()

        # 如果矩阵内是空的，那么可以直接对半得到左括号
        if not self.matrix_labels:
            return self[:len(self) // 2]

        # 如果矩阵内有东西，先得到第一个元素的下标，那么这个下标往前就是左括号
        elem = self._get_element(self.matrix_labels[0])[0]
        index = self.children.index(elem)
        return self[:index]

    def get_right_brace(self) -> Group[SVGElemItem]:
        '''
        获取右大括号元素

        需要在构造 :class:`TypstMatrix` 时传入 ``label=True`` 启用
        '''
        self._raise_if_not_labelled()

        # 如果矩阵内是空的，那么可以直接对半得到右括号
        if not self.matrix_labels:
            return self[len(self) // 2:]

        # 如果矩阵内有东西，先得到最后一个元素的下标，那么这个下标往后就是右括号
        elem = self._get_element(self.matrix_labels[-1])[-1]
        index = self.children.index(elem)
        return self[index + 1:]

    def _raise_if_not_labelled(self) -> None | NoReturn:
        if not self.labelled:
            raise InvalidOrdinalError(_('Matrix indexing requires label=True'))
