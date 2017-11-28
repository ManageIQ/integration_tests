from __future__ import print_function

import click
from pathlib2 import Path


def _is_yaml_file(path):
    return path.suffix in ('.yaml', '.eyaml')


def _warn_on_unknown_encryption(path):
    if path.suffix == '.eyaml' and not Path('.yaml_key').is_file():
            print(
                "WARNING:", path, "is encrypted, "
                "please remember follow the documentation on yaml keys")


def _warn_on_missmatching_symlink(src, target):
    if target.resolve() != src.resolve():
        print("WARNING:", target, "does not point to", src)
        print("         please verify this is intended")


def _warn_on_existing_file(target):
    print('WARNING: You have', target.name, 'as file in your conf/ folder.')
    print('         Please ensure its up2date with the actual configuration.')
    print('         Local overrides can be stored in a .local.yaml file')
    print('         to prevent staleness.')


@click.command()
@click.argument('src', type=click.Path(file_okay=False))
@click.argument('dest', type=click.Path(exists=True, file_okay=False))
def main(src, dest):
    """links configfiles from one folder to another

    if links exists it verifies content
    if files exist at the target side it errors

    Args:
        src: source folder
        dest: target folder
    """
    src = Path(src)
    if not src.exists():
        print("WARNING:", src, "does not exist, skipping linking")
        return

    dest = Path(dest)

    for element in filter(_is_yaml_file, src.iterdir()):
        _warn_on_unknown_encryption(element)
        target = dest.joinpath(element.name)
        # the following is fragile
        if target.is_symlink():
            _warn_on_missmatching_symlink(src=element, target=target)
        elif target.is_file():
            _warn_on_existing_file(target)
        else:
            target.symlink_to(element.resolve())


if __name__ == '__main__':
    main()
