import subprocess
import sys

import py


def main():
    here = py.path.local(__file__).dirpath()
    sys.exit(subprocess.call([
        'docker', 'build', '-t', 'py_test_base', str(here / 'pytestbase')
    ]))


if __name__ == "__main__":
    main()
