import re
import subprocess
import sys
from pprint import PrettyPrinter

import click
import yaml

from cfme.utils.path import get_rel_path
from cfme.utils.path import project_path
from cfme.utils.path import requirements_path
from requirements import RepoImportScanner


# Check for default template exists, its passed to freeze if so
# if user passes bad path for --extra-template, freeze will hit RuntimeError
DEFAULT_EXTRA_TEMPLATE = requirements_path.join("template_non_imported.txt")

# These files is written out to, don't have to assert it exists yet
DEFAULT_SCAN_TEMPLATE = requirements_path.join("template_scanned_imports.txt")
DEFAULT_FROZEN_OUTPUT = requirements_path.join("frozen.txt")
DEFAULT_CONSTRAINT_FILE = requirements_path.join("constraints.txt")

# Package map
DEFAULT_PACKAGE_MAP_FILE = requirements_path.join("package_map.yaml")


# ---- utility functions --------------
def get_package_map(package_map_file):
    package_map = None
    try:
        with open(package_map_file, 'r') as f:
            package_map = yaml.safe_load(f).get("packages")
    except FileNotFoundError:
        pass
    return package_map


def remove_dup_packages(package_list, package):
    # get name from package
    name = re.split("[=><]", package)[0]
    # turn package_list into list of package_names
    package_names = [
        re.split("[=><]", package_name)[0] for package_name in package_list
    ]
    # get rid of duplicate names
    duplicate_indices = [
        i for i, package_name in enumerate(package_names) if package_name == name
    ]
    # get rid of all occurrences except the last since the last will be the recently appended item
    if len(duplicate_indices) > 1:
        del package_list[duplicate_indices[0:-1]]
    return package_list


def add_package_to_file(file_name, package):
    """ Add the package to the file. """
    click.echo(f"Adding {package} to {file_name}")

    # get the lines
    with open(file_name, "r") as f:
        lines = f.readlines()

    # add newline character, if needed
    if not package.endswith("\n"):
        package = f"{package}\n"

    # append the new package
    lines.append(package)
    # remove the package name if present
    lines = remove_dup_packages(lines, package)
    # sorting
    if lines[0].startswith("-c"):
        # don't sort the "-c <constraints-file> line"
        lines[1:] = sorted(lines[1:])
    else:
        lines = sorted(lines)

    with open(file_name, "w") as f:
        # write the (sorted) lines back into the file
        f.writelines(lines)


def remove_package_from_file(file_name, package, is_constraint_file=False):
    """ Removes a package from a requirements file. If the package is not present, does nothing """

    # get the lines
    with open(file_name, "r") as f:
        lines = f.readlines()

    if is_constraint_file:
        # get just the package names
        mod_lines = [
            f"{re.split('[=><]', package_name)[0]}\n" for package_name in lines
        ]
        index_to_remove = [
            i for i, package_name in enumerate(mod_lines)
            if package_name.replace("\n", "") == package
        ]
    else:
        index_to_remove = [
            i for i, package_name in enumerate(lines) if package_name.replace("\n", "") == package
        ]

    if len(index_to_remove) > 1:
        raise ValueError(f"Got more than one package '{package}' to remove from {file_name}. Please"
                         f"check package name!")
    if index_to_remove:
        del lines[index_to_remove[0]]
        # now write modified lines back to file
        with open(file_name, "w") as f:
            f.writelines(lines)
        click.echo(f"Package '{package}' removed from {file_name}")
    else:
        # if index_to_remove is empty, package not found in file
        click.echo(f"Package '{package}' not found in {file_name}")
        return


# ----- Command line function defs -------
@click.group(help="Functions for adding, updating, and freezing requirements")
def main():
    pass


scan_template_opt = click.option(
    '--scan-template',
    'scan_template',
    show_default=True,
    default=get_rel_path(str(DEFAULT_SCAN_TEMPLATE)),
    help='The path to the template file (pip -r arg) for scanned imports, will be overwritten',
)


extra_template_opt = click.option(
    '--extra-template',
    'extra_template',
    show_default=True,
    default=get_rel_path(str(DEFAULT_EXTRA_TEMPLATE)),
    help='The path to the template file (pip -r arg) for extra packages (e.g. pre-commit)'
         ', will be overwritten',
)

constraint_opt = click.option(
    '--constraint-file',
    'constraint_file',
    show_default=True,
    default=get_rel_path(str(DEFAULT_CONSTRAINT_FILE)),
    help='The path to the constraint file (pip -r arg) for extra packages (e.g. pre-commit)'
         ', will be overwritten',
)


frozen_opt = click.option(
    '--frozen-file',
    'frozen_file',
    show_default=True,
    default=get_rel_path(str(DEFAULT_FROZEN_OUTPUT)),
    help='The path to the frozen file for ALL imports',
)


package_map_opt = click.option(
    '--package-map',
    'package_map',
    show_default=True,
    default=get_rel_path(str(DEFAULT_PACKAGE_MAP_FILE)),
    help='The path to the package map for tricky imports'
)


@main.command(help="Scan repository files for imports from pip-installable packages")
@scan_template_opt
@constraint_opt
@package_map_opt
def scan(scan_template, constraint_file, package_map):
    scanner = RepoImportScanner(
        path=str(project_path),
        output=scan_template,
        package_map=get_package_map(package_map)
    )
    scanner.import_statement = re.compile(r"^\s*(?:from|import) ([a-zA-Z0-9-_]+)(?:.*)",
                                          re.MULTILINE)
    click.echo("Scanning repo for imported packages...this may take some time (<10 mins)")
    scan = scanner.run()
    scan.libraries_found.sort()
    pretty_printer = PrettyPrinter()
    click.echo("Found the following packages imported:")
    pretty_printer.pprint(scan.libraries_found)
    scan.output()  # writes to the output file
    # add '-c <constraints-file>' to top of the file
    constraint_short_name = constraint_file.split("/")[-1]
    newlines = [f"-c {constraint_short_name}\n"]
    with open(scan_template, "r") as f:
        lines = f.readlines()
    newlines.extend(lines)
    with open(scan_template, "w") as f:
        f.writelines(newlines)


@main.command(help="Freeze all requirements (non-imported and imported)")
@frozen_opt
def freeze(frozen_file):
    click.echo(f"Freezing requirements to {frozen_file}")
    with open(frozen_file, 'w') as f:
        subprocess.call(['pip', 'freeze', '--exclude-editable'], stdout=f)


@main.command(help="Add and install/update a package to current virtualenv.")
@scan_template_opt
@extra_template_opt
@constraint_opt
@click.argument(
    'package_name',
)
@click.option(
    '-e',
    '--extra',
    'extra_package',
    show_default=True,
    is_flag=True,
    default=False,
    help="Is the package an extra package, i.e. not imported"
)
@click.option(
    "--upgrade",
    "upgrade_or_not",
    show_default=True,
    is_flag=True,
    default=False,
    help="Upgrade an existing package to the most recent version."
)
def add(
    package_name, scan_template, extra_template, extra_package, constraint_file, upgrade_or_not
):
    click.echo(f"Adding package {package_name} to requirements")
    # If there is a <, >, or = present in the package name then constraints are needed
    constraints_needed = bool(re.search("[=><]", package_name))
    if constraints_needed:
        # get the package name
        name = re.split("[=><]", package_name)[0]
    else:
        name = package_name

    # try to install the package
    if upgrade_or_not:
        commands = ["pip", "install", "--upgrade", package_name]
    else:
        commands = ["pip", "install", package_name]
    process = subprocess.run(commands)
    if process.returncode != 0:
        click.echo(f"Unable to install {package_name}")
        sys.exit(1)

    # now add the package to the things
    if constraints_needed:
        # constraints file
        add_package_to_file(constraint_file, package_name)
    if extra_package:
        # extra package file
        add_package_to_file(extra_template, name)
    else:
        # scanned imports file
        add_package_to_file(scan_template, name)


@main.command(help="Remove and uninstall a package from the current virtualenv.")
@scan_template_opt
@extra_template_opt
@constraint_opt
@click.argument(
    'package_name',
)
def remove(package_name, scan_template, extra_template, constraint_file):
    commands = ["pip", "uninstall", "-y", package_name]
    process = subprocess.run(commands)
    if process.returncode != 0:
        click.echo(f"Unable to uninstall {package_name}")
        sys.exit(1)
    # now remove the package from all the files
    for file_name in [scan_template, extra_template]:
        remove_package_from_file(file_name, package_name)
    remove_package_from_file(constraint_file, package_name, is_constraint_file=True)


@main.command(help="Scan and update all packages that are not constrained")
@scan_template_opt
@extra_template_opt
@frozen_opt
@click.option(
    '-f',
    '--freeze',
    'freeze_or_not',
    show_default=True,
    default=False,
    is_flag=True,
    help="Freeze requirements after updating."
)
@click.pass_context
def upgrade_all(ctx, scan_template, extra_template, freeze_or_not, frozen_file):
    ctx.invoke(scan, scan_template=scan_template)
    click.echo(f"Updating packages in {scan_template}...")
    subprocess.call(["pip", "install", "--upgrade", "-r", f"{scan_template}"])
    click.echo(f"Updating packages in {extra_template}...")
    subprocess.call(["pip", "install", "--upgrade", "-r", f"{extra_template}"])
    # freeze new requirements if desired
    if freeze_or_not:
        ctx.invoke(freeze, frozen_file=frozen_file)


@main.command(help="Upgrade (or downgrade) a package to version specified, or latest version")
@constraint_opt
@extra_template_opt
@scan_template_opt
@click.argument(
    'package_name',
)
@click.pass_context
@click.option(
    '-e',
    '--extra',
    'extra_package',
    show_default=True,
    is_flag=True,
    default=False,
    help="Is the package an extra package, i.e. not imported"
)
def upgrade(ctx, constraint_file, extra_template, scan_template, package_name, extra_package):
    constraints_needed = bool(re.search("[=><]", package_name))
    if constraints_needed:
        ctx.forward(add)
    else:
        ctx.forward(add, upgrade_or_not=True)
    # remove the package from constraints file if it was previously constrained
    if not constraints_needed:
        remove_package_from_file(constraint_file, package_name, is_constraint_file=True)
