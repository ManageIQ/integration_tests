import subprocess
import py
import sys

BASE = py.path.local(__file__).dirpath().join('pytestbase')


def build_image(input, tag, no_cache=False):
    command = [
        'docker', 'build',
        '-t', tag + ':latest',
        '-t', tag,
    ]
    if no_cache:
        command.append('--no-cache')
    if input.check(file=1):
        with input.open() as fp:
            return subprocess.call(command + ['-'], stdin=fp)
    else:
        return subprocess.call(command + [str(input)])


sys.exit(
    build_image(BASE / "Dockerfile.base", 'cfmeqe/dockerbot-base') or

    build_image(BASE / "Dockerfile.checkouts", 'cfmeqe/dockerbot-checkouts') or
    build_image(BASE, 'py_test_base', no_cache=True)
)
