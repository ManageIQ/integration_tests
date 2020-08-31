import argparse
import hashlib
import json
import os
import subprocess
import sys

from cfme.scripting.quickstart.proc import PRISTINE_ENV
from cfme.scripting.quickstart.proc import run_cmd_or_exit
from cfme.scripting.quickstart.system import install_system_packages

CREATED = object()

REQUIREMENT_FILE = 'requirements/frozen.txt'
if sys.version_info.major != 3 and sys.version_info.minor >= 7:
    print("ERROR: quickstart only runs in python 3.7+")
    sys.exit(2)

IN_VENV = os.path.exists(os.path.join(sys.prefix, 'pyvenv.cfg'))
IN_LEGACY_VIRTUALENV = getattr(sys, 'real_prefix', None) is not None
IN_VIRTUAL_ENV = IN_VENV or IN_LEGACY_VIRTUALENV


def mk_parser(default_venv_path):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mk-virtualenv", default=default_venv_path)
    parser.add_argument("--system-site-packages", action="store_true")
    parser.add_argument("--config-path", default="../cfme-qe-yamls/complete/")
    parser.add_argument("--debuginfo-install", action="store_true")
    return parser


def args_for_current_venv():
    parser = mk_parser(sys.prefix)
    return parser.parse_args([])


def pip_json_list(venv):
    os.environ.pop('PYTHONHOME', None)
    proc = subprocess.Popen([
        os.path.join(venv, 'bin/pip3'),
        'list', '--format=json',
    ], stdout=subprocess.PIPE)
    return json.load(proc.stdout)


def setup_virtualenv(target, use_site):
    # check for bin in case "venv" is a precreated empty folder
    if os.path.isdir(os.path.join(target, 'bin')):
        print("INFO: Virtualenv", target, "already exists, skipping creation")
        ret = CREATED  # object that can be checked against to see if the venv exists
    else:
        add = ['--system-site-packages'] if use_site else []
        run_cmd_or_exit([sys.executable, '-m', 'venv', target] + add)
        ret = None
    venv_call(target,
              'pip3', 'install', '-U',
              # pip wheel and setuptools are updated just in case
              # since enterprise distros ship versions that are too stable
              # for our purposes
              'pip', 'wheel', 'setuptools',
              # setuptools_scm and docutils installation prevents
              # missbehaved packages from failing
              'setuptools_scm', 'docutils', 'pbr')
    return ret  # used for venv state


def venv_call(venv_path, command, *args, **kwargs):
    # pop PYTHONHOME to avoid nested environments
    os.environ.pop('PYTHONHOME', None)
    run_cmd_or_exit([
        os.path.join(venv_path, 'bin', command),
    ] + list(args), **kwargs)


def hash_file(path):
    content_hash = hashlib.sha1()
    with open(path, 'rb') as fp:
        content_hash.update(fp.read())
    return content_hash.hexdigest()


def install_requirements(venv_path, quiet=False):

    remember_file = os.path.join(venv_path, '.cfme_requirements_hash')
    current_hash = hash_file(REQUIREMENT_FILE)
    if os.path.isfile(remember_file):
        with open(remember_file) as fp:
            last_hash = fp.read()
    elif os.path.exists(remember_file):
        sys.exit(f"ERROR: {remember_file} is required to be a file")
    else:
        last_hash = None
    if last_hash == current_hash:
        print("INFO: skipping requirement installation as frozen ones didn't change")
        print("      to enforce please invoke pip manually")
        return
    elif last_hash is not None:
        current_packages = pip_json_list(venv_path)
        print("INFO:", REQUIREMENT_FILE, 'changed, updating virtualenv')

    venv_call(
        venv_path,
        'pip3', 'install',
        '-r', REQUIREMENT_FILE,
        '--no-binary', 'pycurl',
        *(['-q'] if quiet else []), long_running=quiet)

    with open(remember_file, 'w') as fp:
        fp.write(current_hash)

    if last_hash is not None:
        updated_packages = pip_json_list(venv_path)
        print_packages_diff(old=current_packages, new=updated_packages)


def pip_version_list_to_map(version_list):
    res = {}
    for item in version_list:
        try:
            res[item['name']] = item['version']
        except KeyError:
            pass
    return res


def print_packages_diff(old, new):
    old_versions = pip_version_list_to_map(old)
    new_versions = pip_version_list_to_map(new)
    print_version_diff(old_versions, new_versions)


def version_changes(old, new):
    names = sorted(set(old) | set(new))
    for name in names:
        initial = old.get(name, 'missing')
        afterwards = new.get(name, 'removed')
        if initial != afterwards:
            yield name, initial, afterwards


def print_version_diff(old, new):
    changes = list(version_changes(old, new))
    if changes:
        print("INFO: changed versions"),
        for name, old, new in changes:
            print("     ", name, old, '->', new)


def self_install(venv_path):
    venv_call(venv_path, 'pip3', 'install', '-q', '-e', '.')


def disable_bytecode(venv_path):
    venv_call(venv_path, 'python3', '-m', 'cfme.scripting.disable_bytecode')


def link_config_files(venv_path, src, dest):
    venv_call(venv_path, 'python3', '-m', 'cfme.scripting.link_config', src, dest)


def ensure_pycurl_works(venv_path):
    venv_call(venv_path, 'python3', '-c', 'import curl', env=PRISTINE_ENV)


def main(args):
    if __package__ is None:
        print("ERROR: quickstart must be invoked as module")
        sys.exit(1)
    install_system_packages(args.debuginfo_install)
    venv_state = setup_virtualenv(args.mk_virtualenv, args.system_site_packages)
    install_requirements(args.mk_virtualenv,
                         quiet=(venv_state is CREATED))  # quiet if the venv already existed
    disable_bytecode(args.mk_virtualenv)
    self_install(args.mk_virtualenv)
    link_config_files(args.mk_virtualenv, args.config_path, 'conf')
    ensure_pycurl_works(args.mk_virtualenv)
    if not IN_VIRTUAL_ENV:
        print("INFO: please remember to activate the virtualenv via")
        print("      .", os.path.join(args.mk_virtualenv, 'bin/activate'))
