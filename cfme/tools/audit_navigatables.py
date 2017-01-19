import inspect
import utils.appliance
import utils.path


def main():

    for path in utils.path.project_path.join('cfme').visit('**.py'):
        module = path.pyimport()

        for clas in vars(module).values():
            if isinstance(clas, type):
                if issubclass(clas, utils.appliance.Navigatable):
                    print(clas)
                    methods = [
                        "{} ({})".format(func[0], func[1].im_func.__module__)
                        for func in inspect.getmembers(clas, inspect.ismethod)
                    ]
                    properties = [
                        prop[0] for prop in inspect.getmembers(
                            clas, lambda o: isinstance(o, property))]
                    if methods:
                        print("\tMethods:")
                        print("\t\t{}".format("\n\t\t".join(methods)))
                    if properties:
                        print("\tProperties")
                        print("\t\t{}".format("\n\t\t".join(properties)))
