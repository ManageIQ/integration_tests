import sys
import os
from . import quickstart
QUICKSTART_DONE = 'MIQ_RUNTEST_QUICKSTART_DONE'


def main():
    if QUICKSTART_DONE not in os.environ:
        quickstart.main(quickstart.parser.parse_args(
            ['--mk-virtualenv', sys.prefix]))
        os.environ[QUICKSTART_DONE] = QUICKSTART_DONE
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        import pytest
        pytest.main()
