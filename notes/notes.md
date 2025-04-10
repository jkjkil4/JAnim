## Relation

```python
class Relation[GRelT: 'Relation'](refresh.Refreshable):
```

具有两个字段：

- `parents: list[GRelT]`
- `children: list[GRelT]`



## 动画

通过 Item 的 `anim` 方法可以得到一个 `MethodTransformArgsBuilder`：

```python
@property
    def anim(self) -> Self:
        from janim.anims.transform import MethodTransformArgsBuilder
        return MethodTransformArgsBuilder(self)
```

### MethodTransformArgsBuilder

实现了 `__getattr__`，效果等价于从 `MethodTransform(self.item)` 中访问对应属性。

### MethodTransform

`MethodTransform` 使用一个字段来编码操作：

- `delayed_actions: list[tuple[MethodTransform.ActionType, str | tuple[tuple, dict]]]`

    其中 `MethodTransform.ActionType` 为一个枚举：

    ```python
    class ActionType(Enum):
            GetAttr = 0
            Call = 1
    ```

`MethodTransform` 实现了 `__call__` 和 `__getattr__` 进行操作的编码：

- `__getattr__` 编码 `(MethodTransform.ActionType.GetAttr, name)`
- `__call__` 编码 `(MethodTransform.ActionType.Call, (args, kwargs))`

另外，Component 类具有一个 `r` 方法，用于获取某一个 Component 所属的物件（即便于返回物件自身继续进行链式调用）

此外，其 `_time_fixed` 方法定义了动画的行为：

- 对 `src_item` 应用 `delayed_actions` 中编码的操作

- 遍历 `src_item` 及其所有子物件，调用 `ItemApperance` 的 `detect_change` 方法

- 调用 `self.align_data()`

- 遍历 `src_item` 及所有子物件

    创建 `_MethodTransform(item,  self.path_func, aligned)` 作为 `sub_updater`

### Animation 基类

具有如下字段：

- `parent: AnimGroup | None`
- `name`
- `is_aligned`
- `t_range`
- `rate_func`
- `rate_funcs`
- `timeline`

#### finalize

```python
def finalize(self) -> None:
    self._align_time(self.timeline.time_aligner)
    self._time_fixed()
```

- `_align_time` 即 `aligner.align(self)`
- `_time_fixed` 由子类实现

#### schedule_show_and_hide

```python
def schedule_show_and_hide(self, item: Item, show_at_begin: bool, hide_at_end: bool) -> None:
    if show_at_begin:
        self.timeline.schedule(self.t_range.at, item.show, root_only=True)
    if hide_at_end:
        self.timeline.schedule(self.t_range.end, item.hide, root_only=True)
```

### ItemAnimation

#### _time_fixed

会调用 `self.stack.append(self)`

### TimeAligner

#### align

用 `align_t` 对传入的 Animation 的字段进行“对齐”

#### align_t

将一个输入的 `t: float` “归化”到一个相近的值。用于将浮点数误差导致的“本应该相同的两个数”重新“对齐”到同一个值。

原理是记录先前用一个列表注册的时间 `t`，然后倒序查找一个在容差范围内的值返回，或者注册为新的 `t`。

### Timeline 中与动画相关的内容

#### schedule

```python
def schedule(self, at: float, func: Callable, *args, **kwargs) -> None:
```

创建 `Timeline.ScheduledTask` 按照 `at` 保持排序插入到 `self.scheduled_tasks` 中

#### forward

```python
def forward(self, dt: float = DEFAULT_DURATION, *, _detect_changes=True, _record_lineno=True):
```

- 如果 `_detect_changes` 为 `True` 则调用 `self.detect_changes_of_all()`

- 从 `self.current_time` 一路演进到 `self.current_time + dt`

    不断从 `self.scheduled_tasks` 的开头抽取符合 `at` 小于 `self.current_time + dt` 的任务并执行

#### detect_changes_of_all

```python
def detect_changes_of_all(self) -> None:
```

相当于对 `self.item_apperances` 中的全部 `item` 和对应 `appr` 调用 `appr.stack.detect_change`

### Timeline 中的 ItemAppearance

Timeline 中有这样一个字段：

- `item_appearances: defaultdict[Item, Timeline.ItemAppearance]`

    初始化为 `defaultdict(lambda: Timeline.ItemAppearance(self.time_aligner))`

#### ItemAppearance

`visibility: list[float]` 表示显示/隐藏时间点，偶数下标为显示，奇数下标为隐藏。

有一个 `stack` 字段，类型为 `AnimStack`

### AnimStack

```python
self.time_aligner = time_aligner

# 在跟踪物件变化时，该变量用于对比物件与先前记录的 Display 对象进行对比
# 如果发生变化，则记录新的 Display 对象
self.prev_display: Display | None = None

# times 和 stacks 的元素是一一对应的
# times 中的元素表示 stacks 中对应位置动画序列的开始时间（以下一个时间点为结束时间）
self.times: list[float] = [0]
self.stacks: list[list[ItemAnimation]] = [[]]
```

这里 `prev_display` 相当于一个“静态动画”。

#### append

```python
def append(self, anim: ItemAnimation) -> None:
```

添加 ItemAnimation。
