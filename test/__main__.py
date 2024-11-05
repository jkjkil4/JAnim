import argparse
import shutil
import unittest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--failfast',
        action='store_true'
    )

    args = parser.parse_args()

    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('test', pattern='test_*.py')

    test_runner = unittest.TextTestRunner(verbosity=2, buffer=True, failfast=args.failfast)
    test_runner.run(test_suite)

    try:
        shutil.rmtree('test/__test_tempdir__')
    except FileNotFoundError:
        pass


if __name__ == '__main__':
    main()
