import os
import sys

from cfme.scripting import quickstart
QUICKSTART_DONE = 'MIQ_RUNTEST_QUICKSTART_DONE'


def main():
    if QUICKSTART_DONE not in os.environ:
        quickstart.main(quickstart.args_for_current_venv())
        os.environ[QUICKSTART_DONE] = QUICKSTART_DONE
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        import pytest
        return pytest.main()
