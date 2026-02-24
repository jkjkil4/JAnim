import argparse
import shutil
import unittest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--failfast',
        action='store_true'
    )
    parser.add_argument(
        '--skip_examples',
        action='store_true',
    )

    args = parser.parse_args()
    if args.skip_examples:
        import examples.test_examples as test_examples
        test_examples.disabled = True

    if not args.skip_examples:
        shutil.rmtree('test/__test_errors__', ignore_errors=True)

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
