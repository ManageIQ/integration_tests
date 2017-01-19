import inspect
import utils.appliance
import utils.path


def relevant_types(module):
    return sorted(
        cls for cls in vars(module).values()
        if isinstance(cls, type) and
        issubclass(cls, utils.appliance.Navigatable) and
        cls is not utils.appliance.Navigatable)


def main():

    for path in utils.path.project_path.join('cfme').visit('**.py'):
        module = path.pyimport()

        for clas in relevant_types(module):
            methods = []
            properties = []
            for name, obj in sorted(vars(clas).items()):
                if inspect.ismethod(obj):
                    methods.append(
                        "{} ({})".format(name, obj.__module__))
                elif isinstance(obj, property):
                    properties.append(name)
            if methods or properties:
                print(clas)
            if methods:
                print("\tMethods:")
                print("\t\t{}".format("\n\t\t".join(methods)))
            if properties:
                print("\tProperties")
                print("\t\t{}".format("\n\t\t".join(properties)))
