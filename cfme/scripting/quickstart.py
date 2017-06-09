from __future__ import print_function

import os
import sys
import argparse
import subprocess
import json
import hashlib

try:
    import distro
except ImportError:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(
            os.path.dirname(__file__))),
        'requirements', 'quickstart',
        'distro-1.0.4-py2.py3-none-any.whl'))
    import distro

parser = argparse.ArgumentParser()
parser.add_argument("--mk-virtualenv", default="../cfme_venv")
parser.add_argument("--system-site-packages", action="store_true")
parser.add_argument("--config-path", default="../cfme-qe-yamls/complete/")

DISTRO_DATA = distro.linux_distribution()[:2]
IS_SCRIPT = sys.argv[0] == __file__
CWD = os.getcwd()  # we expect to be in the workdir
IS_ROOT = os.getuid() == 0
REDHAT_BASED = os.path.isfile('/etc/redhat-release')
CREATED = object()
REQUIREMENT_FILE = 'requirements/frozen.txt'
HAS_DNF = os.path.exists('/usr/bin/dnf')
IN_VIRTUALENV = getattr(sys, 'real_prefix', None) is not None

PRISTINE_ENV = dict(os.environ)

REDHAT_PACKAGES_OLD = (
    " python-virtualenv gcc postgresql-devel libxml2-devel"
    " libxslt-devel zeromq3-devel libcurl-devel"
    " redhat-rpm-config gcc-c++ openssl-devel"
    " libffi-devel python-devel tesseract"
    " freetype-devel")


REDHAT_PACKAGES_F25 = (
    " python2-virtualenv gcc postgresql-devel libxml2-devel"
    " libxslt-devel zeromq3-devel libcurl-devel"
    " redhat-rpm-config gcc-c++ openssl-devel"
    " libffi-devel python2-devel tesseract"
    " freetype-devel")

REDHAT_PACKAGES_F26 = (
    " python2-virtualenv gcc postgresql-devel libxml2-devel"
    " libxslt-devel zeromq-devel libcurl-devel"
    " redhat-rpm-config gcc-c++ openssl-devel"
    " libffi-devel python2-devel tesseract"
    " freetype-devel")


if REDHAT_BASED:
    os.environ['PYCURL_SSL_LIBRARY'] = 'nss'
    if DISTRO_DATA == ("Fedora", "25"):
        REDHAT_PACKAGES = REDHAT_PACKAGES_F25
    elif DISTRO_DATA == ("Fedora", "26"):
        REDHAT_PACKAGES = REDHAT_PACKAGES_F26
    else:
        REDHAT_PACKAGES = REDHAT_PACKAGES_OLD

    if HAS_DNF:
        INSTALL_COMMAND = 'dnf install -y'
    else:
        INSTALL_COMMAND = 'yum install -y'
    if not IS_ROOT:
        INSTALL_COMMAND = 'sudo ' + INSTALL_COMMAND


def command_text(command, shell):
    if shell:
        return command
    else:
        command = [repr(x) if ' ' in x else x for x in command]
        return ' '.join(command)


def call_or_exit(command, shell=False, **kw):
    try:
        print('QS $', command_text(command, shell))
        res = subprocess.call(command, shell=shell, **kw)
    except Exception as e:
        print(repr(e))
        sys.exit(1)
    else:
        if res:
            print("call failed with", res)
            sys.exit(res)


def pip_json_list(venv):
    os.environ.pop('PYTHONHOME', None)
    proc = subprocess.Popen([
        os.path.join(venv, 'bin/pip'),
        'list', '--format=json',
    ], stdout=subprocess.PIPE)
    return json.load(proc.stdout)


def install_system_packages():
    if REDHAT_BASED:
        call_or_exit(INSTALL_COMMAND + REDHAT_PACKAGES, shell=True)
    else:
        print("WARNING: unknown distribution,",
              "please ensure you have the required packages installed")
        print("INFO: on redhat based systems this is the equivalend of:")
        print("$ dnf install -y", REDHAT_PACKAGES_OLD)


def setup_virtualenv(target, use_site):
    if os.path.isdir(target):
        print("INFO: Virtualenv", target, "already exists, skipping creation")
        return CREATED
    add = ['--system-site-packages'] if use_site else []

    call_or_exit(['virtualenv', target] + add)
    venv_call(target,
              'pip', 'install', '-U',
              # setuptools_scm and docutils installation prevents
              # missbehaved packages from failing
              'pip', 'wheel', 'setuptools_scm', 'docutils')


def venv_call(venv_path, command, *args, **kwargs):
    # pop PYTHONHOME to avoid nested environments
    os.environ.pop('PYTHONHOME', None)
    call_or_exit([
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
        with open(remember_file, 'r') as fp:
            last_hash = fp.read()
    elif os.path.exists(remember_file):
        sys.exit("ERROR: {} is required to be a file".format(remember_file))
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
        'pip', 'install',
        '-r', REQUIREMENT_FILE,
        '--no-binary', 'pycurl',
        *(['-q'] if quiet else []))

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
    names = sorted(set(old) & set(new))
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
    venv_call(venv_path, 'pip', 'install', '-q', '-e', '.')


def disable_bytecode(venv_path):
    venv_call(venv_path, 'python', '-m', 'cfme.scripting.disable_bytecode')


def link_config_files(src, dest):
    if not os.path.isdir(src):
        print("WARNING: not linking config files,", src, "missing")
        return

    bad_elements = False

    for element in os.listdir(src):
        if element.endswith(('.yaml', '.eyaml')):
            if element.endswith('.eyaml') and not os.path.exists('.yaml_key'):
                print(
                    "WARNING:", element, "is encrypted, "
                    "please remember follow the documentation on yaml keys")
            target = os.path.join(dest, element)
            source = os.path.relpath(os.path.join(src, element), dest)
            # the following is fragile
            if os.path.islink(target):
                if os.readlink(target) != source:
                    print("WARNING:", target, "does not point to", source)
                    print("         please verify this is intended")
            elif os.path.isfile(target):
                print('ERROR: You have', element, 'copied into your conf/ folder. Remove it.')
                bad_elements = True
            else:
                os.symlink(source, target)

    if bad_elements:
        exit(1)


def ensure_pycurl_works(venv_path):
    venv_call(venv_path, 'python', '-c', 'import curl', env=PRISTINE_ENV)


def main(args):
    if not IN_VIRTUALENV:
        # invoked from outside, its ok to be slow
        install_system_packages()
    else:
        print("INFO: skipping installation of system packages from inside of virtualenv")
    venv_state = setup_virtualenv(
        args.mk_virtualenv, args.system_site_packages)
    install_requirements(args.mk_virtualenv, quiet=(venv_state is CREATED))
    disable_bytecode(args.mk_virtualenv)
    self_install(args.mk_virtualenv)
    link_config_files(args.config_path, 'conf')
    ensure_pycurl_works(args.mk_virtualenv)
    if not IN_VIRTUALENV:
        print("INFO: please remember to activate the virtualenv via")
        print("      .", os.path.join(args.mk_virtualenv, 'bin/activate'))


def run_for_current_env(mk_virtualenv=sys.prefix,):
    main(parser.parse_args(['--mk-virtualenv', sys.prefix]))


if IS_SCRIPT:
    main(parser.parse_args())
