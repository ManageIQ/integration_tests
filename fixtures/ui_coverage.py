"""UI Coverage for a CFME/MIQ Appliance

Usage
-----

``py.test --ui-coverage``

General Notes
-------------
simplecov can merge test results, but doesn't appear to like working in a
multi-process environment. Specifically, it clobbers its own results when running
simultaneously in multiple processes. To solve this, each process records its
output to its own directory (configured in coverage_hook). All of the
individual process' results are then manually merged (coverage_merger) into one
big json result, and handed back to simplecov which generates the compiled html
(for humans) and rcov (for jenkins) reports.

thing_toucher makes a best-effort pass at requiring all of the ruby files in
the rails root, as well as any external MIQ libs/utils outside of the rails
root (../lib and ../lib/util). This makes sure files that are never
required still show up in the coverage report.

Workflow Overview
-----------------

Pre-testing (``pytest_configure`` hook):
1. Add ``Gemfile.dev.rb`` to the rails root, then run bundler to install simplecov
   and its dependencies.
2. Install and require the coverage hook (copy ``coverage_hook`` to config/, add
   require line to the end of ``config/boot.rb``)
3. Restart EVM (Rudely) to start running coverage on the appliance processes:
   ``killall -9 ruby; service evmserverd start``
4. TOUCH ALL THE THINGS (run ``thing_toucher.rb`` with the rails runner).
   Fork this process off and come back to it later

Post-testing (``pytest_unconfigure`` hook):
1. Poll ``thing_toucher`` to make sure it completed; block if needed.
2. Stop EVM, but nicely this time so the coverage atexit hooks run:
   ``service evmserverd stop``
3. Run ``coverage_merger.rb`` with the rails runner, which compiles all the individual process
   reports and runs coverage again, additionally creating an rcov report
4. Pull the coverage dir back for parsing and archiving
5. For fun: Read the results from ``coverage/.last_run.json`` and print it to the test terminal/log

Post-testing (e.g. ci environment):
1. Use the generated rcov report with the ruby stats plugin to get a coverage graph
2. Zip up and archive the entire coverage dir for review

"""
# Currently, this only supports running coverage on the appliance in env['base_url'].
# We'll want to aggregate coverage across multiple appliances at some point;
# please keep that in mind when reviewing or altering this module.
import json
import traceback
from functools import partial
from multiprocessing import Process

import pytest
from py.path import local

from cfme.fixtures.pytest_selenium import base_url
from scripts.wait_for_appliance_ui import check_appliance_ui
from utils.log import logger
from utils.path import log_path, scripts_path
from utils.ssh import SSHClient

rails_root = local('/var/www/miq/vmdb')
coverage_data = partial(scripts_path.join, 'data', 'coverage')
gemfile = coverage_data('Gemfile.dev.rb')
coverage_hook = coverage_data('coverage_hook.rb')
coverage_merger = coverage_data('coverage_merger.rb')
thing_toucher = coverage_data('thing_toucher.rb')
coverage_output_dir = log_path.join('coverage')


class UiCoveragePlugin(object):
    def __init__(self):
        self.ssh_client = SSHClient()

    # trylast so that terminalreporter's been configured before ui-coverage
    @pytest.mark.trylast
    def pytest_configure(self, config):
        # Eventually, the setup/teardown work for coverage should be handled by
        # utils.appliance.Appliance to make multi-appliance support easy
        self.reporter = config.pluginmanager.getplugin('terminalreporter')
        self.reporter.write_sep('-', 'Setting up UI coverage reporting')
        self.install_simplecov()
        self.install_coverage_hook()
        self.restart_evm()
        self.touch_all_the_things()
        check_appliance_ui(base_url())

    def pytest_unconfigure(self, config):
        self.reporter.write_sep('-', 'Waiting for coverage to finish and collecting reports')
        self.stop_touching_all_the_things()
        self.merge_reports()
        self.collect_reports()
        self.print_report()

    def install_simplecov(self):
        logger.info('Installing coverage gems on appliance')
        self.ssh_client.put_file(gemfile.strpath, rails_root.strpath)
        x, out = self.ssh_client.run_command('cd {}; bundle'.format(rails_root))
        return x == 0

    def install_coverage_hook(self):
        logger.info('Installing coverage hook on appliance')
        # Put the coverage hook in the miq lib path
        self.ssh_client.put_file(
            coverage_hook.strpath, rails_root.join('..', 'lib', coverage_hook.basename).strpath
        )
        replacements = {
            'require': r"require 'coverage_hook'",
            'config': rails_root.join('config').strpath
        }
        # grep/echo to try to add the require line only once
        # This goes in preinitializer after the miq lib path is set up,
        # which makes it so ruby can actually require the hook
        command_template = (
            'cd {config};'
            'grep -q "{require}" preinitializer.rb || echo -e "\\n{require}" >> preinitializer.rb'
        )
        x, out = self.ssh_client.run_command(command_template.format(**replacements))
        return x == 0

    def restart_evm(self, rude=True):
        logger.info('Restarting EVM to enable coverage reporting')
        # This is rude by default (issuing a kill -9 on ruby procs), since the most common use-case
        # will be to set up coverage on a freshly provisioned appliance in a jenkins run
        if rude:
            x, out = self.ssh_client.run_command('killall -9 ruby; service evmserverd start')
        else:
            x, out = self.ssh_client.run_comment('service evmserverd restart')
        return x == 0

    def touch_all_the_things(self):
        logger.info('Establishing baseline overage by requiring ALL THE THINGS')
        # send over the thing toucher
        self.ssh_client.put_file(
            thing_toucher.strpath, rails_root.join(thing_toucher.basename).strpath
        )
        # start it in an async process so we can go one testing while this takes place
        self._thing_toucher_proc = Process(target=_thing_toucher_mp_handler, args=[self.ssh_client])
        self._thing_toucher_proc.start()

    def stop_touching_all_the_things(self):
        logger.info('Waiting for baseline coverage generator to finish')
        # block while the thing toucher is still running
        self._thing_toucher_proc.join()
        return self._thing_toucher_proc.exitcode == 0

    def merge_reports(self):
        logger.info("Merging coverage reports on appliance")
        # install the merger script
        self.ssh_client.put_file(
            coverage_merger.strpath, rails_root.join(coverage_merger.basename).strpath
        )
        # don't async this one since it's happening in unconfigure
        # merge/clean up the coverage reports
        x, out = self.ssh_client.run_rails_command('coverage_merger.rb')
        return x == 0

    def collect_reports(self):
        coverage_dir = log_path.join('coverage')
        # clean out old coverage dir if it exists
        if coverage_dir.check():
            coverage_dir.remove(rec=True, ignore_errors=True)
        # Then ensure the the empty dir exists
        coverage_dir.ensure(dir=True)
        # then copy the remote coverage dir into it
        logger.info("Collecting coverage reports to {}".format(coverage_dir.strpath))
        logger.info("Report collection can take several minutes")
        self.ssh_client.get_file(
            rails_root.join('coverage').strpath,
            log_path.strpath,
            recursive=True
        )

    def print_report(self):
        try:
            last_run = json.load(log_path.join('coverage', '.last_run.json').open())
            coverage = last_run['result']['covered_percent']
            # TODO: Make the happy vs. sad coverage color configurable, and set it to something
            # good once we know what good is
            style = {'bold': True}
            if coverage > 40:
                style['green'] = True
            else:
                style['red'] = True
            self.reporter.line('UI Coverage Result: {}%'.format(coverage), **style)
        except KeyboardInterrupt:
            # don't block this, so users can cancel out
            raise
        except:
            logger.error('Error printing coverage report to terminal, traceback follows')
            logger.error(traceback.format_exc())


def _thing_toucher_mp_handler(ssh_client):
    # module-level function for use in a subprocess to kick off the thing toucher
    x, out = ssh_client.run_rails_command('thing_toucher.rb')
    return x


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--ui-coverage', dest='ui_coverage', action='store_true', default=False,
        help="Enable setup and collection of ui coverage on an appliance")


def pytest_cmdline_main(config):
    # Only register the plugin worker if ui coverage is enabled
    if config.option.ui_coverage:
        config.pluginmanager.register(UiCoveragePlugin(), name="ui-coverage")
