# -*- coding: utf-8 -*-
import atexit
import inspect
import re
import subprocess

# import diaper for backward compatibility
import diaper


def lazycache(wrapped_method):
    """method decorator to create a lazily-evaluated and cached property

    ``lazycache``'d properties are complete object descriptors, supporting
    ``get``, ``set``, and ``del``, though ``del`` will clear a property's cache rather
    than destroy the property entirely

    Usage:

        >>> from utils import lazycache
        >>> class Example(object):
        ...     @lazycache
        ...     def lazyprop(self):
        ...             return '42'
        ...
        >>> ex = Example()
        >>> value = ex.lazyprop
        >>> print value
        42
        >>> print value is ex.lazyprop
        # lazyprop guarantees this to be True, normal properties do not.
        True
        >>> ex.lazyprop = '99'
        >>> print ex.lazyprop
        # setting works!
        99
        >>> del(ex.lazyprop)
        >>> print ex.lazyprop
        # deleting clears the cache, so the value is recomputed on the next call
        42

    Values are stored in a private attribute of the same name as the method being decorated,
    e.g. a decorated method named ``lazyprop`` will store its cached value in an attr
    called ``_lazyprop``
    """
    attr = '_' + wrapped_method.__name__

    if wrapped_method.__doc__:
        doc = wrapped_method.__doc__ + '\n\nThis attribute is lazily evaluated and cached.'
    else:
        doc = None

    def get_lazy(self):
        if not hasattr(self, attr):
            setattr(self, attr, wrapped_method(self))
        return getattr(self, attr)

    def set_lazy(self, value):
        setattr(self, attr, value)

    def del_lazy(self):
        if hasattr(self, attr):
            delattr(self, attr)

    lazy = property(get_lazy, set_lazy, del_lazy, doc)
    return lazy


def property_or_none(wrapped, *args, **kwargs):
    """property_or_none([fget[, fset[, fdel[, doc]]]])
    Property decorator that turns AttributeErrors into None returns

    Useful for chained attr lookups where some links in the chain are None

    Note:

        This delegates back to the :py:func:`property <python:property>` builtin and inherits
        its signature; thus it can be used interchangeably with ``property``.

    """
    def wrapper(store):
        try:
            return wrapped(store)
        except AttributeError:
            pass
    return property(wrapper, *args, **kwargs)


class _classproperty(property):
    """Subclass property to make classmethod properties possible"""
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


def classproperty(f):
    """Enables properties for whole classes:

    Usage:

        >>> class Foo(object):
        ...     @classproperty
        ...     def bar(cls):
        ...         return "bar"
        ...
        >>> print Foo.bar
        baz
    """
    return _classproperty(classmethod(f))


def at_exit(f, *args, **kwargs):
    """Diaper-protected atexit handler registering. Same syntax as atexit.register()"""
    return atexit.register(lambda: diaper(f, *args, **kwargs))


def normalize_text(text):
    text = re.sub(r"[^a-z0-9 ]", "", text.strip().lower())
    return re.sub(r"\s+", " ", text)


class kwargify(object):
    def __init__(self, function):
        self._f = function
        self._defaults = {}
        self._args = inspect.getargspec(self._f).args
        f_defaults = inspect.getargspec(function).defaults
        if f_defaults is not None:
            for key, value in zip(self._args[-len(f_defaults):], f_defaults):
                self._defaults[key] = value

    def __call__(self, **kwargs):
        args = []
        for arg in self._args:
            if arg in kwargs:
                args.append(kwargs[arg])
            elif arg in self._defaults:
                args.append(self._defaults[arg])
            else:
                raise TypeError("Required parameter {} not found in the context!".format(arg))
        return self._f(*args)

    @property
    def __name__(self):
        return self._f.__name__


def tries(num_tries, exceptions, f, *args, **kwargs):
    """ Tries to call the function multiple times if specific exceptions occur.

    Args:
        num_tries: How many times to try if exception is raised
        exceptions: Tuple (or just single one) of exceptions that should be treated as repeat.
        f: Callable to be called.
        *args: Arguments to be passed through to the callable
        **kwargs: Keyword arguments to be passed through to the callable

    Returns:
        What ``f`` returns.

    Raises:
        What ``f`` raises if the try count is exceeded.
    """
    tries = 0
    while tries < num_tries:
        tries += 1
        try:
            return f(*args, **kwargs)
        except exceptions as e:
            pass
    else:
        raise e


def read_env(file):
    """Given a py.path.Local file name, return a dict of exported shell vars and their values

    Note:

        This will only include shell variables that are exported from the file being parsed

    Returns a dict of varname: value pairs. If the file does not exist or bash could not parse
    the file, this dict will be empty.

    """
    env_vars = {}
    if file.check():
        with file.open() as f:
            content = f.read()

        # parse the file with bash, since it's pretty good at it, and dump the env
        command = ['bash', '-c', 'source {} && env'.format(file.strpath)]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1)

        # filter out vars not defined
        for line in iter(proc.stdout.readline, b''):
            try:
                key, value = line.split("=", 1)
            except ValueError:
                continue
            if '{}='.format(key) in content:
                env_vars[key] = value.strip()
        stdout, stderr = proc.communicate()
    return env_vars


def deferred_verpick(version_d):
    """This turns a dictionary for verpick to a class property.

    Useful for verpicked constants.
    """
    from utils.version import pick as _version_pick

    @classproperty
    def getter(self):
        return _version_pick(version_d)
    return getter
