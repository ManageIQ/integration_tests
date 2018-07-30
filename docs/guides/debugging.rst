Debugging
=========

Pytest has a cool feature to enable a debugger on failures. Just provide an additional
command line option::

    pytest --pdb

By default only python builtin debugger is supported. It's not much convinient to
use. There is another python debugger called pudb. It requires only two packages
to be installed::

    pip install pytest-pudb pudb

Then you can use it in such way::

    pytest some_test --pudb

Links
^^^^^

https://github.com/inducer/pudb

https://github.com/wronglink/pytest-pudb
