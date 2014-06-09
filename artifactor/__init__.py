"""
Artifactor

Artifactor is used to collect artifacts from a number of different plugins and put them into
one place. Artifactor works around a series of events and is geared towards unit testing, though
it is extensible and customizable enough that it can be used for a variety of purposes.

The main guts of Artifactor is around the plugins. Before Artifactor can do anything it must have
a configured plugin. This plugin is then configured to bind certain functions inside itself
to certain events. When Artifactor is triggered to handle a certain event, it will tell the plugin
that that particular event has happened and the plugin will respond accordingly.

In addition to the plugins, Artifactor can also run certain callback functions before and after
the hook function itself. These are call pre and post hook callbacks. Artifactor allows multiple
pre and post hook callbacks to be defined per event, but does not guarantee the order that they
are executed in.

To allow data to be passed to and from hooks, Artifactor has the idea of global and event local
values. The global values persist in the Artifactor instance for its lifetime, but the event local
values are destroyed at the end of each event.

Let's take the example of using the unit testing suite py.test as an example for Artifactor.
Suppose we have a number of tests that run as part of a test suite and we wish to store a text
file that holds the time the test was run and its result. This information is required to reside
in a folder that is relevant to the test itself. This type of job is what Artifactor was designed
for.

To begin with, we need to create a plugin for Artifactor. Consider the following piece of code::

    from artifactor import ArtifactorBasePlugin
    import time


    class Test(ArtifactorBasePlugin):

        def plugin_initialize(self):
            self.register_plugin_hook('start_test', self.start_test)
            self.register_plugin_hook('finish_test', self.finish_test)

        def start_test(self, test_name, test_location, artifact_path):
            filename = artifact_path + "-" + self.ident + ".log"
            with open(filename, "w") as f:
                f.write(test_name + "\n")
                f.write(str(time.time()) + "\n")

        def finish_test(self, test_name, artifact_path, test_result):
            filename = artifact_path + "-" + self.ident + ".log"
            with open(filename, "w+") as f:
                f.write(test_result)

This is a typical plugin in Artifactor, it consists of 2 things. The first item is
the special function called ``plugin_initialize()``. This is important
and is equivilent to the ``__init__()`` that would usually be found in a class definition.
Artifactor calls ``plugin_initialize()`` for each plugin as it loads it.
Inside this section we register the hook functions to their associated events. Each event
can only have a single function associated with it. Event names are able to be freely assigned
so you can customize plugins to work to specific events for your use case.
The ``register_plugin_hook()`` takes an event name as a string and a function to callback when
that event is experienced.

Next we have the hook functions themselves, ``start_test()`` and ``finish_test()``. These
have arguments in their prototypes and these arguments are supplied by Artifactor and are
created either as arguments to the ``fire_hook()`` function, which is responsible for actually
telling Artifactor that an even has occured, or they are created in the pre hook script.

Artifactor uses the global and local values referenced earlier to store these argument values.
When a pre, post or hook callback finishes, it has the opportunity to supply updates to both
the global and local values dictionaries. In doing this, a pre-hook script can prepare data,
which will could be stored in the locals dictionary and then passed to the actual plugin hook
as a keyword argument. Local values override global values.

We need to look at an example of this, but first we must configure artifactor and the plugin::

    log_dir: /home/me/artiout
    per_run: run #test, run, None
    overwrite: True
    artifacts:
        test:
            enabled: True
            plugin: test

Here we have defined a ``log_dir`` which will be the root of all of our artifacts. We have asked
Artifactor to group the artifacts by run, which means that it will try to create a directory
under the ``log_dir`` which indicates which test "run" this was. We can also specify a value of
"test" here, which will move the test run identifying folder up to the leaf in the tree.

The ``log_dir`` and contents of the config are stored in global values as ``log_dir`` and
``artifactor_config`` respectively. These are the only two global values which are setup by
Artifactor.

This data is then passed to artifactor as a dict, we will assume a variable name of ``config`` here.

Let's consider how we would run this test

    art = artifactor.artifactor
    art.set_config(config)
    art.register_plugin(test.Test, "test")
    artifactor.initialize()

    a.fire_hook('start_session', run_id=2235)
    a.fire_hook('start_test', test_name="my_test", test_location="tests/mytest.py")
    a.fire_hook('finish_test', test_name="my_test", test_location="tests/mytest.py",
        test_result="FAILED")
    a.fire_hook('finish_session')

The art.register_plugin is used to bind a plugin name to a class definition. Notice in the config
section earlier, we have a ``plugin: test`` field. This name ``test`` is what Artifactor will
look for when trying to find the appropriate plugin. When we register the plugin with the
``register_plugin`` function, we take the ``test.Test`` class and essentially give it the name
``test`` so that the names will tie up and the plugin will be used.

Notice that we have sent some information to along with the request to fire the hook. Ignoring the
``start_session`` event for a minute, the ``start_test`` event sends a ``test_name`` and a
``test_location``. However, the ``start_test`` hook also required an argument called
``argument_path``. This is not supplied by the hook, and isn't setup as a global value, so how does
it get there?

Inside Artifactor, by default, a pre_hook callback called ``start_test()`` is bound to the
``start_test`` event. This callback returns a local values update which includes ``artifact_path``.
This is how the artifact_path is returned. This hook can be removed, by running a
``unregister_hook_callback`` with the name of the hook callback.

"""
from artifactor.utils import parse_setup_dir, start_session
from riggerlib import Rigger, RiggerClient
import os
import sys
import traceback
from utils import create_logger


class Artifactor(Rigger):
    """A sub from Rigger"""

    def set_config(self, config):
        self.config = config

    def parse_config(self):
        """
        Reads the config data and sets up values
        """
        if not self.config:
            return False
        self.log_dir = self.config.get('log_dir', None)
        log_file_name = os.path.join(self.log_dir, "artifactor_log.txt")
        self.logger = create_logger('artifactor_logger', log_file_name)
        if not os.path.isdir(self.log_dir):
            os.makedirs(self.log_dir)
        self.squash_exceptions = self.config.get('squash_exceptions', False)
        if not self.log_dir:
            print "!!! Log dir must be specified in yaml"
            sys.exit(127)
        self.setup_plugin_instances()
        self.start_server()
        self.global_data = {'artifactor_config': self.config, 'log_dir': self.config['log_dir'],
                            'artifacts': dict()}

    def handle_failure(self, exc):
        self.logger.debug(exc[0])
        self.logger.debug(exc[1])
        self.logger.debug(traceback.format_tb(exc[2]))

    def log_message(self, message):
        self.logger.debug(message)

artifactor = Artifactor(None)


def initialize():
    artifactor.parse_config()
    artifactor.register_hook_callback('start_test', 'pre', parse_setup_dir,
                                      name="default_start_test")
    artifactor.register_hook_callback('finish_test', 'pre', parse_setup_dir,
                                      name="default_finish_test")
    artifactor.register_hook_callback('start_session', 'pre', start_session,
                                      name="default_start_session")
    artifactor.initialized = True


class ArtifactorClient(RiggerClient):
    pass
