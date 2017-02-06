from rope.base.project import Project
from rope.refactor.move import MoveModule

project = Project('.')

utils = project.find_module('utils')
move = MoveModule(project, utils)
cfme = project.find_module('cfme')
print(cfme)
changes = move.get_changes(cfme)
changes.do()
