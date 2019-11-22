import atexit
import os
import re
import subprocess
import threading
from contextlib import contextmanager
from functools import partial

import diaper
from cached_property import cached_property
from werkzeug.local import LocalProxy
# import diaper for backward compatibility

on_rtd = os.environ.get('READTHEDOCS') == 'True'


class TriesExceeded(Exception):
    """Default exception raised when tries() method doesn't catch a func exception"""
    pass


class FakeObject(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs


def fakeobject_or_object(obj, attr, default=None):
    if isinstance(obj, str):
        return FakeObject(**{attr: obj})
    elif not obj:
        return FakeObject(**{attr: default})
    else:
        return obj


def clear_property_cache(obj, *names):
    """
    clear a cached property regardess of if it was cached priority
    """
    if isinstance(obj, LocalProxy):
        obj = obj._get_current_object()
    for name in names:
        assert isinstance(getattr(type(obj), name), cached_property)
        obj.__dict__.pop(name, None)


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
        >>> print(Foo.bar)
        baz
    """
    return _classproperty(classmethod(f))


def at_exit(f, *args, **kwargs):
    """Diaper-protected atexit handler registering. Same syntax as atexit.register()"""
    return atexit.register(lambda: diaper(f, *args, **kwargs))


def _prenormalize_text(text):
    """Makes the text lowercase and removes all characters that are not digits, alphas, or spaces"""
    # _'s represent spaces so convert those to spaces too
    return re.sub(r"[^a-z0-9 ]", "", text.strip().lower().replace('_', ' '))


def _replace_spaces_with(text, delim):
    """Contracts spaces into one character and replaces it with a custom character."""
    return re.sub(r"\s+", delim, text)


def normalize_text(text):
    """Converts a string to a lowercase string containing only letters, digits and spaces.

    The space is always one character long if it is present.
    """
    return _replace_spaces_with(_prenormalize_text(text), ' ')


def attributize_string(text):
    """Converts a string to a lowercase string containing only letters, digits and underscores.

    Usable for eg. generating object key names.
    The underscore is always one character long if it is present.
    """
    return _replace_spaces_with(_prenormalize_text(text), '_')


def normalize_space(text):
    """Works in accordance with the XPath's normalize-space() operator.

    `Description <https://developer.mozilla.org/en-US/docs/Web/XPath/Functions/normalize-space>`_:

        *The normalize-space function strips leading and trailing white-space from a string,
        replaces sequences of whitespace characters by a single space, and returns the resulting
        string.*
    """
    return _replace_spaces_with(text.strip(), ' ')


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
    caught_exception = TriesExceeded('Tries were exhausted without a func exception')
    tries = 0
    while tries < num_tries:
        tries += 1
        try:
            return f(*args, **kwargs)
        except exceptions as e:
            caught_exception = e
            pass
    else:
        raise caught_exception


# There are some environment variables that get smuggled in anyway.
# If there is yet another one that will be possibly smuggled in, update this entry.
READ_ENV_UNWANTED = {'SHLVL', '_', 'PWD'}


def read_env(file):
    """Given a :py:class:`py.path.Local` file name, return a dict of exported shell vars and their
    values.

    Args:
        file: A :py:class:`py.path.Local` instance.

    Note:
        This will only include shell variables that are exported from the file being parsed

    Returns:
        A :py:class:`dict` of key/value pairs. If the file does not exist or bash could not
        parse the file, this dict will be empty.
    """
    env_vars = {}
    if file.check():
        # parse the file with bash, since it's pretty good at it, and dump the env
        # Use env -i to clean up the env (except the very few variables provider by bash itself)
        command = ['env', '-i', 'bash', '-c', 'source {} && env'.format(file.strpath)]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=1)

        # filter out the remaining unwanted things
        for line in iter(proc.stdout.readline, b''):
            try:
                key, value = line.split("=", 1)
            except ValueError:
                continue
            if key not in READ_ENV_UNWANTED:
                try:
                    value = int(value.strip())
                except (ValueError, TypeError):
                    value = value.strip()
                env_vars[key] = value
        stdout, stderr = proc.communicate()
    return env_vars


def safe_string(o):
    """This will make string out of ANYTHING without having to worry about the stupid Unicode errors

    This function tries to make str/unicode out of ``o`` unless it already is one of those and then
    it processes it so in the end there is a harmless ascii string.

    Args:
        o: Anything.
    """
    if not isinstance(o, str):
        o = str(o)
    if isinstance(o, bytes):
        o = o.decode('utf-8', "ignore")
    if not isinstance(o, str):
        o = o.encode("ascii", "xmlcharrefreplace")
    else:
        o = o.encode("ascii", "xmlcharrefreplace").decode('ascii')
    return o


def process_pytest_path(path):
    # Processes the path elements with regards to []
    path = path.lstrip("/")
    if len(path) == 0:
        return []
    try:
        seg_end = path.index("/")
    except ValueError:
        seg_end = None
    try:
        param_start = path.index("[")
    except ValueError:
        param_start = None
    try:
        param_end = path.index("]")
    except ValueError:
        param_end = None
    if seg_end is None:
        # Definitely a final segment
        return [path]
    else:
        if (param_start is not None and param_end is not None and seg_end > param_start and
                seg_end < param_end):
            # The / inside []
            segment = path[:param_end + 1]
            rest = path[param_end + 1:]
            return [segment] + process_pytest_path(rest)
        else:
            # The / that is not inside []
            segment = path[:seg_end]
            rest = path[seg_end + 1:]
            return [segment] + process_pytest_path(rest)


def process_shell_output(value):
    """This function allows you to unify the behaviour when you putput some values to stdout.

    You can check the code of the function how exactly does it behave for the particular types of
    variables. If no output is expected, it returns None.

    Args:
        value: Value to be outputted.

    Returns:
        A tuple consisting of returncode and the output to be printed.
    """
    result_lines = []
    exit = 0
    if isinstance(value, (list, tuple, set)):
        for entry in sorted(value):
            result_lines.append(entry)
    elif isinstance(value, dict):
        for key, value in value.items():
            result_lines.append('{}={}'.format(key, value))
    elif isinstance(value, str):
        result_lines.append(value)
    elif isinstance(value, bool):
        # 'True' result becomes flipped exit 0, and vice versa for False
        exit = int(not value)
    else:
        # Unknown type, print it
        result_lines.append(str(value))

    return exit, '\n'.join(result_lines) if result_lines else None


def iterate_pairs(iterable):
    """Iterates over iterable, always taking two items at time.

    Eg. ``[1, 2, 3, 4, 5, 6]`` will yield ``(1, 2)``, then ``(3, 4)`` ...

    Must have even number of items.

    Args:
        iterable: An iterable with even number of items to be iterated over.
    """
    if len(iterable) % 2 != 0:
        raise ValueError('Iterable must have even number of items.')
    it = iter(iterable)
    for i in it:
        yield i, next(it)


def icastmap(t, i, *args, **kwargs):
    """Works like the map() but is made specially to map classes on iterables. A generator version.

    This function only applies the ``t`` to the item of ``i`` if it is not of that type.

    Args:
        t: The class that you want all the yielded items to be type of.
        i: Iterable with items to be cast.

    Returns:
        A generator.
    """
    for item in i:
        if isinstance(item, t):
            yield item
        else:
            yield t(item, *args, **kwargs)


def castmap(t, i, *args, **kwargs):
    """Works like the map() but is made specially to map classes on iterables.

    This function only applies the ``t`` to the item of ``i`` if it is not of that type.

    Args:
        t: The class that you want all theitems in the list to be type of.
        i: Iterable with items to be cast.

    Returns:
        A list.
    """
    return list(icastmap(t, i, *args, **kwargs))


class InstanceClassMethod(object):
    """ Decorator-descriptor that enables you to use any method both as class and instance one

    Usage:

    .. code-block:: python

        class SomeClass(object):
            @InstanceClassMethod
            def a_method(self):
                the_instance_variant()

            @a_method.classmethod
            def a_method(cls):
                the_class_variant()

        i = SomeClass()
        i.a_method()
        SomeClass.a_method()
        # Both are possible

    If you don't pass ``classmethod`` the "instance" method, the one that was passed first will
    be called for both kinds of invocation.
    """
    def __init__(self, instance_or_class_method):
        self.instance_or_class_method = instance_or_class_method
        self.class_method = None

    def classmethod(self, class_method):
        self.class_method = class_method
        return self

    def __get__(self, o, t):
        if o is None:
            # classmethod
            return partial(self.class_method or self.instance_or_class_method, t)
        else:
            # instancemethod
            return partial(self.instance_or_class_method, o)


class ParamClassName(object):
    """ ParamClassName is a Descriptor to help when using classes and instances as parameters

    Note: This descriptor is a hack until collections are implemented everywhere

    Usage:

    .. code-block:: python

        class Provider(object):
            _param_name = ParamClassName('name')

            def __init__(self, name):
                self.name = name

    When accessing the ``_param_name`` on the class object it will return the ``__name__`` of the
    class by default. When accessing the ``_param_name`` on an instance of the class, it will return
    the attribute that is passed in.
    """

    def __init__(self, instance_attr, class_attr='__name__'):
        self.instance_attr = instance_attr
        self.class_attr = class_attr

    def __get__(self, instance, owner):
        if instance:
            return getattr(instance, self.instance_attr)
        else:
            return getattr(owner, self.class_attr)


@contextmanager
def periodic_call(period_seconds, call, args=None, kwargs=None):
    timer = None
    args = args or []
    kwargs = kwargs or {}

    def timer_event():
        call(*args, **kwargs)
        reschedule()

    def reschedule():
        nonlocal timer
        timer = threading.Timer(period_seconds, timer_event)
        timer.start()

    reschedule()
    try:
        yield
    finally:
        timer.cancel()
