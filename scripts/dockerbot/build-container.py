from __future__ import print_function, absolute_import
import subprocess
import argparse
from pathlib2 import Path
import shutil
import sys


parser = argparse.ArgumentParser()
parser.add_argument('--no-cache', action='store_true')


HERE = Path(__file__).resolve().parent
BASE = HERE / 'pytestbase'

REPO = BASE / 'temporary_git_repo/integration_tests'
CWD = Path.cwd()


def cwdstr(maybe_path):
    if isinstance(maybe_path, Path) and CWD in maybe_path.parents:
        return str(maybe_path.relative_to(CWD))
    else:
        return str(maybe_path)


def call(*command_parts, **kw):
    cwd = kw.get('cwd')
    if cwd is not None:
        cwd = str(cwd)
    command = []
    for elements in command_parts:
        if isinstance(elements, (list, tuple)):
            command.extend(map(cwdstr, elements))
        else:
            command.append(cwdstr(elements))
    res = subprocess.call(command, cwd=cwd)
    print(res, 'from', command)
    return res


def build_image(dockerfile, context_dir, tag=None, no_cache=False):
    assert tag
    command = [
        'docker', 'build',
        '-t', tag + ':latest',
        '-t', tag,
    ]

    if no_cache:
        command.append('--no-cache')
    return call(command, [context_dir, '-f', dockerfile])


def re_setup_repo():
    if REPO.exists():
        shutil.rmtree(str(REPO))
    return call(
        ['git', 'clone', HERE.parent.parent, REPO]
    ) or call(
        ['git', 'checkout', '-b', 'master'],
        cwd=REPO,
    )


def main(options):
    sys.exit(
        re_setup_repo() or

        build_image(
            BASE / "Dockerfile.base", context_dir=BASE,
            tag='cfmeqe/dockerbot-base', no_cache=options.no_cache) or
        build_image(
            BASE / "Dockerfile.checkouts",
            context_dir=BASE, tag='cfmeqe/dockerbot-checkouts', no_cache=True) or
        build_image(
            BASE / "Dockerfile",
            context_dir=BASE, tag='py_test_base', no_cache=True)
    )


if __name__ == '__main__':
    main(parser.parse_args())
