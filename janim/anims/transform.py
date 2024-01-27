from janim.anims.animation import Animation
from janim.items.item import Item
from janim.utils.data import AlignedData


class Transform(Animation):
    def __init__(
        self,
        src_item: Item,
        target_item: Item,
        *,
        hide_src: bool = True,
        show_target: bool = True,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.src_item = src_item
        self.target_item = target_item

        self.hide_src = hide_src
        self.show_target = show_target

        self.root_only = root_only

    def anim_init(self) -> None:
        '''
        进行物件数据的对齐
        '''
        self.aligned: dict[tuple[Item, Item], AlignedData[Item.Data]] = {}

        def align(item1: Item, item2: Item, recurse: bool) -> None:
            tpl = (item1, item2)
            if tpl in self.aligned:
                return

            data1 = self.timeline.get_stored_data_at_right(item1, self.global_range.at)
            data2 = self.timeline.get_stored_data_at_left(item2, self.global_range.end)
            aligned = self.aligned[tpl] = data1.align_for_interpolate(data1, data2)

            if recurse:
                for child1, child2 in zip(aligned.data1.children, aligned.data2.children):
                    align(child1, child2, True)

        align(self.src_item, self.target_item, not self.root_only)

        if self.hide_src:
            self.timeline.schedule(self.global_range.at, self.src_item.hide, root_only=self.root_only)
        if self.show_target:
            self.timeline.schedule(self.global_range.end, self.target_item.show, root_only=self.root_only)

    def anim_on_alpha(self, alpha: float) -> None:
        '''
        对物件数据进行过渡插值
        '''
        for aligned in self.aligned.values():
            aligned.union.interpolate(aligned.data1, aligned.data2, alpha)

    def render(self) -> None:
        for aligned in self.aligned.values():
            aligned.union.render()
