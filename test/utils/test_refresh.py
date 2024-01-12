import unittest

import janim.utils.refresh as refresh


class MyItem(refresh.Refreshable):
    def __init__(self) -> None:
        super().__init__()

        # 用于记录 `get_data` 真正被调用的次数
        # Used to record the actual number of times `get_data` is called
        self.cnt = 0

        self.data = 0

    @refresh.register
    def get_data(self) -> None:
        self.cnt += 1
        return self.data


class SubItem(MyItem):
    @property
    @refresh.register
    def empty_list(self) -> None:
        return []


class RefreshTest(unittest.TestCase):
    def test_refresh(self) -> None:
        item = MyItem()

        # 一开始没调用 `get_data`，因此显然调用次数为 0
        # Initially, `get_data` is not called, so the call count is obviously 0
        self.assertEqual(item.cnt, 0)

        # 在这十次中，只有第一次是有真正执行 `get_data` 的，因此执行后调用次数为 1
        # Out of these ten times, only the first one actually executes `get_data`,
        # so the call count after execution is 1
        for _ in range(10):
            item.get_data()
        self.assertEqual(item.cnt, 1)

        # 这里设置了 `data` 为 10，但是由于没有标记需要更新，
        # 因此 `get_data` 的数据并没有被更新，所以应当为 0
        # Here, `data` is set to 10, but since there is no mark for an update,
        # the data of `get_data` is not updated, so it should be 0
        item.data = 10
        self.assertEqual(item.get_data(), 0)

        # 这里标记需要更新，所以 `get_data` 可以得到更新，并且调用次数变为 2
        # Marking for an update, so `get_data` gets updated, and the call count becomes 2
        item.mark_refresh(item.get_data)
        self.assertEqual(item.cnt, 1)
        self.assertEqual(item.get_data(), 10)
        self.assertEqual(item.cnt, 2)

        # 之后这十次调用都没有真正调用 `get_data`，所以最终调用次数仍然为 2
        # In the subsequent ten calls, `get_data` is not actually called,
        # so the final call count remains 2
        for _ in range(10):
            item.get_data()
        self.assertEqual(item.cnt, 2)

    def test_refresh_with_inherit(self) -> None:
        s = SubItem()

        self.assertEqual(s.cnt, 0)
        s.get_data()
        s.get_data()
        self.assertEqual(s.cnt, 1)

        lst_id = s.empty_list
        self.assertIs(lst_id, s.empty_list)

        s.mark_refresh('empty_list')
        self.assertIsNot(lst_id, s.empty_list)

        lst_id = s.empty_list
        s.reset_refresh()
        self.assertIsNot(lst_id, s.empty_list)


# if __name__ == '__main__':
#     unittest.main()
