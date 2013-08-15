## Scenario tests

The tests in this directory are designed to setup and configure CFME. These are destructive tests whose purpose is to automate reference architectures and other customer workflows.

### Running scenarios

1. Copy `tests/scenarios/<my_scenario>/data/cfme_data.yaml.template` and rename `cfme_data.yaml`.
2. Run as `py.test tests/scenarios/<my_scenario> --cfmedata=path/to/scenario/data/cfme_data.yaml`

Tests in the scenarios directory will not be discovered by the py.test collection unless py.test is pointed at the scenarios directory.

### Data

The data subdirectory in each scenario is where the corresponding data files are placed. In it you will need to rename and customize the `cfme_data.yaml.template` file. The tests shall be generic and be driven by scenario data fixtures (`conftest.py`) plus the scenario data directory.

### TODO

 * Move more of the test workflows into service methods in cfme_pages repo so the tests are very simple. This will make test duplication more tolerable.
 * Better still, consider ways to order test collection via py.test hooks. This would allow tests to move to a higher level directory and become a library that multiple scenarios could access.
