## Scenario tests

The tests in this directory are designed to setup and configure CFME. These are destructive tests whose purpose is to automate reference architectures and other customer workflows.

### Running scenarios

1. Copy `tests/scenarios/<my_scenario>/data/cfme_data.yaml.template` and rename `cfme_data.yaml`.
2. Run as `py.test tests/scenarios/<my_scenario> --cfmedata=path/to/scenario/data/cfme_data.yaml`

Tests in the scenarios directory will not be discovered by the py.test collection unless py.test is pointed at the scenarios directory.

### Data

The data subdirectory in each scenario is where the corresponding data files are placed. In it you will need to rename and customize the `cfme_data.yaml.template` file.
