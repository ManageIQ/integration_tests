from __future__ import print_function, absolute_import
import subprocess
import py
import sys

HERE = py.path.local(__file__).dirpath()
BASE = HERE.join('pytestbase')

REPO = BASE.join('temporary_git_repo/integration_tests')
CWD = py.path.local()


def cwdstr(maybe_path):
    if isinstance(maybe_path, py.path.local):
        return maybe_path.relto(CWD) or '.'  # fragile
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
    if REPO.check(dir=True):
        REPO.remove()
    return call(
        ['git', 'clone', HERE.dirpath().dirpath(), REPO]
    ) or call(
        ['git', 'checkout', '-b', 'master'],
        cwd=REPO,
    )


sys.exit(
    re_setup_repo() or

    build_image(
        BASE / "Dockerfile.base", context_dir=BASE,
        tag='cfmeqe/dockerbot-base') or
    build_image(
        BASE / "Dockerfile.checkouts",
        context_dir=BASE, tag='cfmeqe/dockerbot-checkouts', no_cache=True) or
    build_image(
        BASE / "Dockerfile",
        context_dir=BASE, tag='py_test_base', no_cache=True)
)
