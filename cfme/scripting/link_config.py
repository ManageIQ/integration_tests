import errno
import os

import click
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


def _is_yaml_file(path):
    return path.suffix in ('.yaml', '.eyaml')


def _warn_on_unknown_encryption(path):
    if path.suffix == '.eyaml' and not Path('.yaml_key').is_file():
        print("WARNING:", path, "is encrypted, please follow the documentation on yaml keys")


def _check_missmatching_symlink(src, target):
    check_passed = True
    if target.resolve() != src.resolve():
        print(
            "WARNING: Different symlink already exists for", target.name, "in your dest. "
            "Skipped this file. Use --force to override.")
        check_passed = False
    return check_passed


def _check_existing_file(target):
    check_passed = True
    if target.is_file():
        print(
            "ERROR: File", target.name, "already exists in your dest. Skipped this file. "
            "Use --force to override.")
        check_passed = False
    return check_passed


@click.command()
@click.argument('src', type=click.Path(file_okay=False))
@click.argument('dest', type=click.Path(exists=True, file_okay=False))
@click.option('--force', is_flag=True)
def main(src, dest, force):
    """links configfiles from one folder to another

    if links exists it verifies content
    if files exist at the target side it errors

    Args:
        src: source folder
        dest: target folder
        force: override existing symlinks
    """
    src = Path(src)
    if not src.exists():
        print("WARNING:", src, "does not exist, skipping linking")
        return

    dest = Path(dest)

    for element in filter(_is_yaml_file, src.iterdir()):
        _warn_on_unknown_encryption(element)
        target = dest.joinpath(element.name)

        if force:
            try:
                target.symlink_to(element.resolve())
            except OSError as e:
                if e.errno == errno.EEXIST:
                    backup_target = Path(dest.joinpath(element.name + "_bak"))
                    print("Replacing", target.name, "and saving backup as", backup_target.name)
                    # Would use 'backup_target.replace()' here but that's only supported in py3
                    if backup_target.exists():
                        os.remove(str(backup_target))
                    target.rename(backup_target)

                    target.symlink_to(element.resolve())
                else:
                    raise
        else:
            if target.is_symlink():
                # If symlink already exists and points to same src, do nothing.
                _check_missmatching_symlink(src=element, target=target)
            elif _check_existing_file(target):
                target.symlink_to(element.resolve())
                print("Symlink created for", target.name)


if __name__ == '__main__':
    main()
