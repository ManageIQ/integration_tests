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
import json
import os
from glob import glob

from py.error import ENOENT
from py.path import local

from fixtures.pytest_store import store
from utils.log import logger
from utils.path import log_path, scripts_data_path

# paths to all of the coverage-related files

# on the appliance
#: Corresponds to Rails.root in the rails env
rails_root = local('/var/www/miq/vmdb')
#: coverage root, should match what's in the coverage hook and merger scripts
appliance_coverage_root = rails_root.join('coverage')

# local
coverage_data = scripts_data_path.join('coverage')
gemfile = coverage_data.join('Gemfile.dev.rb')
coverage_hook = coverage_data.join('coverage_hook.rb')
coverage_merger = coverage_data.join('coverage_merger.rb')
thing_toucher = coverage_data.join('thing_toucher.rb')
coverage_output_dir = log_path.join('coverage')


def _thing_toucher_mp_handler(ssh_client):
    # for use in a subprocess to kick off the thing toucher
    x, out = ssh_client.run_rails_command('thing_toucher.rb')
    return x


def clean_coverage_dir():
    try:
        coverage_output_dir.remove(ignore_errors=True)
    except ENOENT:
        pass
    coverage_output_dir.ensure(dir=True)


class UiCoveragePlugin(object):
    def pytest_configure(self, config):
        if store.parallelizer_role != 'master':
            store.current_appliance.install_coverage()

        if store.parallelizer_role != 'slave':
            clean_coverage_dir()

    def pytest_sessionfinish(self, exitstatus):
        # Now master/standalone needs to move all the reports to an appliance for the source report
        if store.parallelizer_role != 'slave':
            store.terminalreporter.write_sep('-', 'collecting coverage reports')
        else:
            store.slave_manager.message('collecting coverage reports')

        if store.parallelizer_role != 'master':
            store.current_appliance.collect_coverage_reports()

        # for slaves, everything is done at this point
        if store.parallelizer_role == 'slave':
            return

        # The rest should be only happening in the master/sandalone process
        results_tgzs = glob(coverage_output_dir.join('*-coverage-results.tgz').strpath)
        if not results_tgzs:
            # Not sure if we should explode here or not.
            logger.error('No coverage results collected')
            store.terminalreporter.write_sep('=', 'No coverage results found', red=True)
            return

        # push the results to the appliance
        ssh_client = store.current_appliance.ssh_client()
        for results_tgz in results_tgzs:
            dest_file = appliance_coverage_root.join(os.path.basename(results_tgz)).strpath
            ssh_client.put_file(results_tgz, dest_file)
            ssh_client.run_command('tar xvaf {} -C /var/www/miq/vmdb/coverage'.format(dest_file))

        # run the merger on the appliance to generate the simplecov report
        store.terminalreporter.write_sep('-', 'merging coverage reports')
        ssh_client.put_file(coverage_merger.strpath, rails_root.strpath)
        ssh_client.run_rails_command(coverage_merger.basename)

        # Now bring the report back and write out the info
        # TODO: We're already using tar, might as well tar this up, too.
        ssh_client.get_file(
            appliance_coverage_root.join('merged').strpath,
            coverage_output_dir.strpath,
            recursive=True
        )

    def pytest_unconfigure(self, config):
        try:
            last_run = json.load(log_path.join('coverage', 'merged', '.last_run.json').open())
            coverage = last_run['result']['covered_percent']
            # TODO: We don't currently know what a "good" coverage number is.
            style = {'bold': True}
            if coverage > 40:
                style['green'] = True
            else:
                style['red'] = True
            store.terminalreporter.line('UI Coverage Result: {}%'.format(coverage), **style)
        except KeyboardInterrupt:
            # don't block this, so users can cancel out
            raise
        except Exception as ex:
            logger.error('Error printing coverage report to terminal')
            logger.exception(ex)


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--ui-coverage', dest='ui_coverage', action='store_true', default=False,
        help="Enable setup and collection of ui coverage on an appliance")


def pytest_cmdline_main(config):
    # Only register the plugin worker if ui coverage is enabled
    if config.option.ui_coverage:
        config.pluginmanager.register(UiCoveragePlugin(), name="ui-coverage")
