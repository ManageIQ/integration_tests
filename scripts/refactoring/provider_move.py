from rope.base import project
from rope.refactor.move import MoveModule
from rope.refactor.rename import Rename

my_project = project.Project('.')

providers_dest = my_project.get_folder('cfme/providers')
if not providers_dest.exists():
    providers_dest.create()

if not providers_dest.get_children():
    providers_dest.create_file('__init__.py')


folders_to_process = ['infrastructure', 'cloud', 'middleware', 'containers']

for folder in folders_to_process:
    def find(fmt):
        return my_project.find_module(fmt.format(folder=folder))

    print(folder)
    print(" append name")
    res = find('cfme.{folder}.provider')
    Rename(my_project, res).get_changes('provider_' + folder).do()
    print(" move")
    res = find('cfme.{folder}.provider_{folder}')
    MoveModule(my_project, res).get_changes(providers_dest).do()
    print(" fix_name")
    res = find('cfme.providers.provider_{folder}')
    Rename(my_project, res).get_changes(folder).do()
    print(" push up elements")
    res = find('cfme.providers.{folder}')
    for item in res.get_children():
        if item.name == '__init__.py':
            continue
        print("  push up " + item.name)
        MoveModule(my_project, item).get_changes(res.parent).do()
    print(" meshing up __init__.py")
    res.get_child('__init__.py').move(
        'cfme/providers/{folder}.py'.format(folder=folder))
