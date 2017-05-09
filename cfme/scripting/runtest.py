import sys
from . import quickstart


def main():
    quickstart.main(quickstart.parser.parse_args(
        ['--mk-virtualenv', sys.prefix]))
    import pytest
    pytest.main()
