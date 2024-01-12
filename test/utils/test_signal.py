import unittest

import janim.utils.refresh as refresh
from janim.utils.signal import Signal


class SignalTest(unittest.TestCase):
    def test_self_signal(self) -> None:
        class User(refresh.Refreshable):
            def __init__(self, name: str):
                super().__init__()

                self.name = name
                self.msg = ''

                # for testing
                self.notifier_counter = 0

            @Signal
            def set_msg(self, msg: str) -> None:
                self.msg = msg
                User.set_msg.emit(self)

            @set_msg.self_slot()
            def notifier(self) -> None:
                self.notifier_counter += 1

            @set_msg.self_refresh()
            @refresh.register
            def get_text(self) -> str:
                return f'[{self.name}] {self.msg}'

        user = User('jkjkil')

        self.assertEqual(user.notifier_counter, 0)
        user.set_msg('hello')
        self.assertEqual(user.notifier_counter, 1)

        self.assertEqual(user.get_text(), '[jkjkil] hello')

    def test_self_signal_with_inherit(self) -> None:
        called_list = []

        class A:
            @Signal
            def test(self) -> None:
                called_list.append(self.test)
                A.test.emit(self)
                A.test.emit(self, key='special')

            @test.self_slot()
            def fnA(self) -> None:
                called_list.append(self.fnA)

        class B(A):
            @A.test.self_slot()
            def fnB(self) -> None:
                called_list.append(self.fnB)

        class C(A):
            @A.test.self_slot()
            def fnC(self) -> None:
                called_list.append(self.fnC)

        class D(C, B):  # test mro()
            @A.test.self_slot()
            def fnD1(self) -> None:
                called_list.append(self.fnD1)

            @A.test.self_slot(key='special')
            def fnD2(self) -> None:
                called_list.append(self.fnD2)

        b = B()
        b.test()

        c = C()
        c.test()

        d = D()
        d.test()

        self.assertEqual(
            called_list,
            [
                b.test,
                b.fnB, b.fnA,
                c.test,
                c.fnC, c.fnA,
                d.test,
                d.fnD1, d.fnC, d.fnB, d.fnA,
                d.fnD2
            ]
        )

    def test_signal(self) -> None:
        called_list = []

        class A:
            @Signal
            def fn_A(self) -> None:
                called_list.append(self.fn_A)
                A.fn_A.emit(self)

            def fn_A2(self) -> None:
                called_list.append(self.fn_A2)

        class B(refresh.Refreshable):
            def fn_B1(self) -> None:
                called_list.append(self.fn_B1)

            @refresh.register
            def fn_B2(self) -> None:
                called_list.append(self.fn_B2)

        a1, a2, b1, b2 = A(), A(), B(), B()

        A.fn_A.connect(a1, a2.fn_A2)
        A.fn_A.connect(a1, a1.fn_A2)
        A.fn_A.connect(a1, b1.fn_B1)
        A.fn_A.connect_refresh(a1, b2, b2.fn_B2)

        def fn() -> None:
            called_list.append(fn)

        fn()
        b2.fn_B2()
        b2.fn_B2()
        fn()
        a1.fn_A()
        fn()
        b2.fn_B2()
        b2.fn_B2()
        b2.fn_B2()
        fn()
        a1.fn_A()
        fn()
        b2.fn_B2()

        self.assertEqual(
            called_list,
            [
                fn,
                b2.fn_B2,
                fn,
                a1.fn_A, a2.fn_A2, a1.fn_A2, b1.fn_B1,
                fn,
                b2.fn_B2,
                fn,
                a1.fn_A, a2.fn_A2, a1.fn_A2, b1.fn_B1,
                fn,
                b2.fn_B2
            ]
        )

    def test_signal_err(self) -> None:
        class A(refresh.Refreshable):
            @Signal
            def fn(self):
                A.fn.emit(self)

            @fn.self_refresh_with_recurse()
            def fn_that_could_not_decorated_with_refresh_with_recurse(self): ...

        a = A()

        with self.assertRaises(TypeError):
            a.fn()


# if __name__ == '__main__':
#     unittest.main()
