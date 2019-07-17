#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
from pathlib import Path
from pprint import PrettyPrinter

from importlib_metadata import metadata
from importlib_metadata import PackageNotFoundError
from pip_module_scanner.scanner import Scanner

from cfme.utils.path import project_path
from requirements import freeze


HERE = Path(__file__).resolve().parent

# Check for default template exists, its passed to freeze if so
# if user passes bad path for --extra-template, freeze will hit RuntimeError
DEFAULT_EXTRA_TEMPLATE = HERE.joinpath("template_non_imported.txt")

# These files is written out to, don't have to assert it exists yet
DEFAULT_SCAN_TEMPLATE = HERE.joinpath("template_scanned_imports.txt")
DEFAULT_FROZEN_OUTPUT = HERE.joinpath("frozen.txt")


parser = argparse.ArgumentParser()
parser.add_argument(
    "--upgrade-only", default=None, help="updates only the given package instead of all of them"
)
parser.add_argument(
    "--scan-only",
    action="store_true",
    help="Stop after scanning and writing out to --template, DO NOT run freeze",
)
parser.add_argument(
    "--template",
    dest="scan_template",
    default=str(DEFAULT_SCAN_TEMPLATE),
    help="The path to the template file. Used for scan output, and freeze",
)
parser.add_argument(
    "--extra-template",
    dest="extra_template",
    default=str(DEFAULT_EXTRA_TEMPLATE),
    help="The path to the template for non-imported packages. Used for freeze",
)
parser.add_argument(
    "--frozen-output",
    dest="frozen_output",
    default=str(DEFAULT_FROZEN_OUTPUT),
    help="The path for the output frozen file. Used for freeze",
)


# Override Scanner to skip dotfiles
class TestScanner(Scanner):
    """Overwrite Scanner to use git tracked files instead of os.walk

    Also override init to create installed_packages since we just want to write package names
    """

    def __init__(self, *args, **kwargs):
        # overwrite libraries_installed keyed on package names
        super(TestScanner, self).__init__(*args, **kwargs)
        self.installed_packages = [
            lib.key
            for lib in self.libraries_installed
            if lib.key not in "manageiq-integration-tests"
        ]  # ignore local

    def search_script_directory(self, path):
        """
        Recursively loop through a directory to find all python
        script files. When one is found, it is analyzed for import statements

        Only scans files tracked by git

        :param path: string
        :return: generator
        """
        proc = subprocess.Popen(["git", "ls-files", "--full-name"], stdout=subprocess.PIPE)
        proc.wait()
        # decode the file names because subprocess PIPE has them as bytes
        for file in [f.decode() for f in proc.stdout.read().splitlines()]:
            if (not file.endswith(".py")) or "sprout/" in file:
                continue  # skip sprout files and non-python files
            self.search_script_file(os.path.dirname(file), os.path.basename(file))

    def search_script(self, script):
        """
        Search a script's contents for import statements and check
        if they're currently prevent in the list of all installed
        pip modules.
        :param script: string
        :return: void
        """
        if self.import_statement.search(script):
            unique_found = []
            for f_import in set(self.import_statement.findall(script)):
                # Try the package metadata lookup, if its not found its just local or builtin
                try:
                    import_metadata = metadata(f_import)
                except PackageNotFoundError:
                    continue

                # Check that the package isn't already accounted for
                name = import_metadata["Name"]
                # Shriver - previously this was checking installed packages
                # Thinking this prevents freeze_all from working correctly on a clean venv
                # Want it to be able to go from clean venv + import scan to a frozen req file
                # freeze.py uses any existing frozen file as constraints
                if name not in self.libraries_found:  # and name in self.installed_packages:
                    unique_found.append(name)

            for package_name in unique_found:
                # Shriver - see above
                # self.installed_packages.remove(package_name)
                self.libraries_found.append(package_name)

    def output_to_fd(self, fd):
        """
        Outputs the results of the scanner to a file descriptor (stdout counts :)
        :param fd: file
        :return: void
        """
        for library in self.libraries_found:
            fd.write("{}\n".format(library))


def main(conf):

    """
    this one simply runs the freezing for all templates

    this is the one you should always use
    """
    scan = TestScanner(path=str(project_path), output=conf.scan_template)
    scan.import_statement = re.compile(r"^\s*(?:from|import) ([a-zA-Z0-9-_]+)(?:.*)", re.MULTILINE)
    scan = scan.run()
    scan.libraries_found.sort()
    pretty_printer = PrettyPrinter()
    print("Found the following packages imported:")
    pretty_printer.pprint(scan.libraries_found)
    scan.output()  # writes to the output file

    if not conf.scan_only:
        pip_templates = [conf.scan_template]
        if Path(conf.extra_template).exists():
            pip_templates.append(conf.extra_template)

        with freeze.maybe_transient_venv_dir(None, False) as venv:
            args = argparse.Namespace(
                venv=venv,
                keep=True,
                templates=pip_templates,
                out=conf.frozen_output,
                upgrade_only=conf.upgrade_only,
            )
            freeze.main(args)


if __name__ == "__main__":
    main(parser.parse_args())
