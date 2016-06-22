import re
import polib
from tempfile import NamedTemporaryFile


class Translate(object):
    def __init__(self, appliance):
        self.appliance = appliance
        self._po = None
        self.lib = None

    @property
    def po(self):
        if not self._po:
            temp_file = NamedTemporaryFile()
            self.appliance.ssh_client.get_file(
                '/var/www/miq/vmdb/config/locales/manageiq.pot', temp_file.name)
            self._po = polib.pofile(temp_file.name)
        return self._po

    def process_entries(self):
        todo = [self.po.untranslated_entries(), self.po.translated_entries()]
        for item in todo:
            for t in item:
                ident = re.findall('QE:\s(.*)', t.comment)
                if ident:
                    self.lib[ident[0]] = t.msgid

    def __getitem__(self, name):
        if not self.lib:
            self.lib = {}
            self.process_entries()
        try:
            return self.lib[name]
        except KeyError:
            return None
