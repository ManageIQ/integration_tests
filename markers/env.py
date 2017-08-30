"""
This file provides multiple markers for environmental parameters

A test can be marked with

@pytest.mark.browser(ALL)
@pytest.mark.browser(NONE)
@pytest.mark.browser('firefox')

At the moment, lists of parameters are not supported

"""
from utils import testgen

ALL = 'all'
NONE = 'none'
ONE = 'one'


class EnvironmentMarker(object):
    """Base Environment Marker"""
    PARAM_BY_DEFAULT = False

    def process_env_mark(self, metafunc):
        if hasattr(metafunc.function, self.NAME):
            if getattr(metafunc.function, self.NAME).args:
                mark_param = getattr(metafunc.function, self.NAME).args[0]
            else:
                raise Exception('No keyword given to mark')
            if mark_param == ALL:
                metafunc.fixturenames.append(self.NAME)
                testgen.parametrize(metafunc, self.NAME, self.CHOICES)
            elif mark_param == ONE:
                metafunc.fixturenames.append(self.NAME)
                testgen.parametrize(metafunc, self.NAME, [self.CHOICES[0]])
            elif mark_param == NONE:
                return
        elif self.PARAM_BY_DEFAULT:
            metafunc.fixturenames.append(self.NAME)
            testgen.parametrize(metafunc, self.NAME, [self.CHOICES[0]])
        else:
            return


class BrowserEnvironmentMarker(EnvironmentMarker):
    """Browser Envrionment Marker"""
    NAME = 'browser'
    CHOICES = ['firefox', 'chrome', 'ie']


class TCPEnvironmentMarker(EnvironmentMarker):
    """TCP Environment Marker"""
    NAME = 'tcpstack'
    CHOICES = ['ipv4', 'ipv6']


class ProviderEnvironmentMarker(EnvironmentMarker):
    NAME = 'provider'

    def process_env_mark(self, metafunc):
        if hasattr(metafunc.function, self.NAME):
            args = getattr(metafunc.function, self.NAME).args
            kwargs = getattr(metafunc.function, self.NAME).kwargs
            print args, kwargs
            scope = kwargs.pop('scope', 'function')
            indirect = kwargs.pop('indirect', False)
            filter_unused = kwargs.pop('filter_unused', True)
            gen_func = kwargs.pop('gen_func', testgen.providers_by_class)

            def fixture_filter(metafunc, argnames, argvalues):
                """Filter fixtures based on fixturenames in the function represented by ``metafunc``"""
                # Identify indeces of matches between argnames and fixturenames
                keep_index = [e[0] for e in enumerate(argnames) if e[1] in metafunc.fixturenames]

                # Keep items at indices in keep_index
                def f(l):
                    return [e[1] for e in enumerate(l) if e[0] in keep_index]

                # Generate the new values
                argnames = f(argnames)
                argvalues = map(f, argvalues)
                return argnames, argvalues

            # If parametrize doesn't get you what you need, steal this and modify as needed
            argnames, argvalues, idlist = gen_func(metafunc, *args, **kwargs)
                # Filter out argnames that aren't requested on the metafunc test item, so not all tests
                # need all fixtures to run, and tests not using gen_func's fixtures aren't parametrized.
            if filter_unused:
                argnames, argvalues = fixture_filter(metafunc, argnames, argvalues)
                # See if we have to parametrize at all after filtering
            testgen.parametrize(metafunc, argnames, argvalues, indirect=indirect, ids=idlist, scope=scope)



def pytest_generate_tests(metafunc):
    print metafunc.function
    markers = [
        BrowserEnvironmentMarker(),
        TCPEnvironmentMarker(),
        ProviderEnvironmentMarker()
    ]
    for marker in markers:
        print marker
        marker.process_env_mark(metafunc)
