from cfme.utils.appliance.implementations.ui import navigate_to


class ValidateStatsMixin(object):
    # TODO: Move this class to a higher level, where could be useful for thing beyond this
    # network module, maybe BaseEntity

    def ui_details_value(self, path, property_name):
        view = navigate_to(self, "Details", use_resetter=False)
        return getattr(view.entities, path).get_text_of(property_name)

    def validate_stats(self, expected_stats):
        """ Validates that the details page matches the expected stats.

        Args:
            expected_stats: dictionary of values to be compered to UI values

        This method is given expected stats as an argument and those are then matched
        against the UI. An AssertionError exception will be raised if the stats retrieved
        from the UI do not match those from expected stats.

        IMPORTANT: Please make sure inherited classes implements `ui_details_value` which fetches
        the value of a stat
        """

        cfme_stats = {
            (path, stat): self.ui_details_value(path, stat) for path, stat in expected_stats
        }
        assert cfme_stats == expected_stats
