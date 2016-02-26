""" Test plugin for Artifactor """

from artifactor import ArtifactorBasePlugin
import time


class Test(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)

    def start_test(self, test_name, test_location, artifact_path):
        filename = artifact_path + "-" + self.ident + ".log"
        with open(filename, "a+") as f:
            f.write(test_name + "\n")
            f.write(str(time.time()) + "\n")
        for i in range(2):
            time.sleep(2)
            print("houh")

    def finish_test(self, test_name, artifact_path):
        print("finished")
