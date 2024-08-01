import unittest


def main() -> None:
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('test', pattern='test_*.py')

    test_runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    test_runner.run(test_suite)


if __name__ == '__main__':
    main()
