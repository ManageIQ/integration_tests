# -*- coding: utf-8 -*-
import click
import sys
from . import quickstart

from IPython.terminal.interactiveshell import TerminalInteractiveShell

IMPORTS = [
    'from utils import conf',
    'from fixtures.pytest_store import store',
    'from utils.appliance.implementations.ui import navigate_to',
    'from utils import providers'
]


@click.command(help="Open an IPython shell")
def main():
    """Use quickstart to ensure we have correct env, then execute imports in ipython and done."""
    quickstart.main(quickstart.parser.parse_args(['--mk-virtualenv', sys.prefix]))
    print('Welcome to IPython designed for running CFME QE code.')
    ipython = TerminalInteractiveShell.instance()
    for code_import in IMPORTS:
        print('> {}'.format(code_import))
        ipython.run_cell(code_import)
    from cfme.utils.path import conf_path
    custom_import_path = conf_path.join('miq_python_startup.py')
    if custom_import_path.exists():
        with open(custom_import_path.strpath, 'r') as custom_import_file:
            custom_import_code = custom_import_file.read()
        print('Importing custom code:\n{}'.format(custom_import_code.strip()))
        ipython.run_cell(custom_import_code)
    else:
        print(
            'You can create your own python file with imports you use frequently. '
            'Just create a conf/miq_python_startup.py file in your repo. '
            'This file can contain arbitrary python code that is executed in this context.')
    ipython.interact()


if __name__ == '__main__':
    main()
