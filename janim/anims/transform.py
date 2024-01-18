from janim.anims.animation import Animation
from janim.items.item import Item
from janim.utils.data import AlignedData


class Transform(Animation):
    def __init__(self, item_from, item_to, *, root_only=False, **kwargs):
        super().__init__(**kwargs)
        self.item_from = item_from
        self.item_to = item_to
        self.root_only = root_only

    def anim_init(self) -> None:
        self.aligned: dict[tuple[Item, Item], AlignedData[Item.Data]] = {}

        def align(item1: Item, item2: Item, recurse: bool) -> None:
            tpl = (item1, item2)
            if tpl in self.aligned:
                return

            data1 = self.timeline.get_stored_data_at_time(item1, self.global_range.at)
            data2 = self.timeline.get_stored_data_at_time(item2, self.global_range.end)
            aligned = self.aligned[tpl] = data1.align_for_interpolate(data1, data2)

            if recurse:
                for child1, child2 in zip(aligned.data1.children, aligned.data2.children):
                    align(child1, child2, True)

        align(self.item_from, self.item_to)

    def anim_on_alpha(self, alpha: float) -> None:
        for aligned in self.aligned.values():
            aligned.union.interpolate(aligned.data1, aligned.data2, alpha)
