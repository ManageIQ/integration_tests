from __future__ import print_function

import click
from pathlib2 import Path


@click.command()
@click.argument('src', type=click.Path(exists=True, file_okay=False))
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
    dest = Path(dest)

    bad_elements = False

    for element in src.iterdir():

        if element.suffix in ('.yaml', '.eyaml'):
            if element.suffix == '.eyaml' and not Path('.yaml_key').is_file():
                print(
                    "WARNING:", element, "is encrypted, "
                    "please remember follow the documentation on yaml keys")
            target = dest.joinpath(element.name)
            # the following is fragile
            if target.is_symlink():
                if target.resolve() != element.resolve():
                    print("WARNING:", target, "does not point to", element)
                    print("         please verify this is intended")
            elif target.is_file():
                print('ERROR: You have', target.name, 'copied into your conf/ folder. Remove it.')
                bad_elements = True
            else:
                target.symlink_to(element.resolve())

    if bad_elements:
        exit(1)


if __name__ == '__main__':
    main()
