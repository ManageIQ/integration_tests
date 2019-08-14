Bugzilla Guide
==============

Contributor guidelines
----------------------
We have developed several tools/workflows to make the process
for dealing with Bugzilla bugs (BZs) easier for contributors.
Here, we discuss:

* :ref:`metadata_markers` for test cases: ``blockers``, ``coverage``, and ``automates``
* the :ref:`miq_bz_command` command
* :ref:`bugzilla_docblock`

.. _metadata_markers:

Metadata Markers
^^^^^^^^^^^^^^^^
* **blockers**: this marker is used when a test case is `blocked` by a bugzilla bug.
  To use this marker simply add a ``@pytest.mark.metadata(blockers=[BZ(<bug_id>])`` decorator
  to your test case. At run time, the property ``BZ(<bug_id>).blocks`` will be checked.
  This property, defined in ``cfme.utils.blockers.py::BZ`` will return ``True`` if the BZ is
  open, not in an ``ON_QA``, ``VERIFIED``, or ``CLOSED`` state, and if the BZ appliance
  version matches (or is lower than) the current appliance version you're testing against.
  If  ``BZ().blocks == True``, the test case will be skipped. For example,

  .. code-block:: python

     @pytest.mark.meta(blockers=[BZ(1234567)])
     def test_blocked():
        """
        This test case is blocked by the BZ with id 1234567
        """
        pass


  There are several key word arguments
  that can be passed to this ``BZ`` class: ``unblock``, ``forced_streams``, ``ignore_bugs``
  etc. ``unblock`` takes a boolean function so that the BZ will not block if some condition is met.
  ``forced_streams`` is to be used when a BZ written against one appliance version is also
  present in another appliance version (and a clone has not yet been made). It will force
  the BZ to block in the other appliance version. **Note**: if a workaround is possible,
  it is better to put ``BZ(<bug_id>).blocks`` in the test case or broken bit of framework,
  so that the test case can still run. Any BZs passed to ``ignore_bugs`` will not block.
* **coverage**: this marker is used to denote `manual` test cases that are providing
  coverage for a specific BZ. Test cases that are marked with this will be
  parsed by the ``miq bz`` command and can set ``qe_test_coverage`` flags on Bugzilla. If
  the test case covers more than one BZ, then you can put multiple entries in the list.
  For example,

  .. code-block:: python

     @pytest.mark.meta(coverage=[1234567, 1234568])
     def test_coverage():
        """
        This test case provides coverage for the BZs 1234567 and 1234568
        """
        pass

* **automates**: this marker is used to denote `automated` test cases that are providing
  coverage for a specific BZ. It is identical to ``coverage`` but meant for automated test
  cases. For example,


  .. code-block:: python

     @pytest.mark.meta(automates=[1234567, 1234568])
     def test_automated():
        """
        This test case provides (poor) automated coverage for the BZs 1234567 and 1234568
        """
        assert True

The markers ``automates`` and ``coverage`` should not be used in the same test case. However,
if a test case is blocked by a BZ and is also providing coverage for that BZ, then you can
use both ``automates OR coverage`` and ``blockers``. Also note that ``blockers`` must be
passed in as an instance the ``BZ`` class from ``cfme.utils.blockers``, but for ``automates``
or ``coverage`` you can pass just the ``id`` or an instance of the ``BZ`` class.

.. _miq_bz_command:

miq bz command
^^^^^^^^^^^^^^
The ``miq bz`` command is a CLI utility for generating reports on BZs that have coverage.
It looks for test cases that are marked with ``automates`` or ``coverage``, and gathers
data about the BZ. Most importantly it looks at whether or not ``qe_test_coverage`` is set to
``+``, ``?``, or ``-``. When you mark a test case with ``automates`` or ``coverage``, you are
saying that the test case is providing ``qe_test_coverage`` for a specific BZ. Therefore, ``qe_test_coverage``
should be ``+`` for that BZ.

The help for this command is:

.. code-block:: console

 Usage: miq bz [OPTIONS] COMMAND [ARGS]...

    Functions for generating reports on BZs included in test suite metadata

    Options:
      --help  Show this message and exit.

    Commands:
      coverage  Set QE test coverage flag based on automates/coverage metadata
      list      List open/closed BZs that have test coverage
      report    Generate BZ report on BZs that have coverage given a directory

And the calling sequence is ``miq bz <command> <directory or test module> <optional-args>``.
For example, say you find a new BZ and write a test case to cover that BZ in
``cfme.tests.control.test_bugs``. Here let's use an actual example from our codebase:

.. code-block:: python

    @pytest.mark.meta(blockers=[BZ(1717483)], automates=[1711352])
    def test_policy_condition_multiple_ors(
            appliance,
            virtualcenter_provider,
            vm_compliance_policy_profile
    ):
        """
        Tests to make sure that policy conditions with multiple or statements work properly

        Bugzilla:
            1711352
            1717483

        Polarion:
            assignee: jdupuy
            caseimportance: low
            casecomponent: Control
            initialEstimate: 1/12h
        """
        collection = appliance.provider_based_collection(virtualcenter_provider)
        all_vms = collection.all()
        all_vm_names = [vm.name for vm in all_vms]

        # we need to select out cu-24x7
        vm_name = virtualcenter_provider.data["cap_and_util"]["capandu_vm"]
        # check that it exists on provider
        if not virtualcenter_provider.mgmt.does_vm_exist(vm_name):
            pytest.skip("No capandu_vm available on virtualcenter_provider of name {}".format(vm_name))

        vms = [all_vms.pop(all_vm_names.index(vm_name))]

        # do not run the policy simulation against more that 4 VMs
        try:
            vms.extend(all_vms[0:min(random.randint(1, len(all_vms)), 4)])
        except ValueError:
            pytest.skip("No other vms exist on provider to run policy simulation against.")

        filtered_collection = collection.filter({"names": [vm.name for vm in vms]})
        # Now perform the policy simulation
        view = navigate_to(filtered_collection, "PolicySimulation")
        # Select the correct policy profile
        view.fill({"form": {"policy_profile": "{}".format(vm_compliance_policy_profile.description)}})

        # Now check each quadicon and ensure that only cu-24x7 is compliant
        for entity in view.form.entities.get_all():
            state = entity.data["quad"]["bottomRight"]["tooltip"]
            if entity.name == vm_name:
                assert state == "Policy simulation successful."
            else:
                assert state == "Policy simulation failed with: false"

This a nice test case because it combines several of the things above. It is `blocked`
by the BZ 1717483, but it is providing automated test coverage for BZ 1711352. Note that it isn't
providing coverage for BZ 1717483, so that BZ must be blocking a setup or teardown step of
the test case. It also makes use of the ``Bugzilla`` docblock, discussed below.
You can then run the following command to set qe_test_coverage to ``+`` for BZ 1711352.

``miq bz coverage --set cfme/tests/control/test_bugs.py``

A dry run of this command (i.e. without ``--set``) produces the following output:

.. code-block:: console

    The following BZs should have qe_test_coverage set to '+':
        id: 1155284, qe_test_coverage: ?
        id: 1243357, qe_test_coverage: ?
        id: 1711352, qe_test_coverage: -

.. _bugzilla_docblock:

Bugzilla docblock
^^^^^^^^^^^^^^^^^
The ``Bugzilla`` docblock is for listing any BZs that are tangentially related to a test case.
Blockers, automates, and coverage BZs should be listed here. Any BZ related to a test case
should also be put here. The BZs listed in this docblock will be shown in the test case
description on Polarion. Therefore, it's useful to list all the BZs related to the test
case here. For example

.. code-block:: python

    @pytest.mark.meta(blockers=[BZ(1234561), automates=[1234567])
    def test_automated():
      """
      This test case is blocked by BZ 1234561, but provides automated test coverage for
      BZ 1234567. The following BZs are related to this test case:

      Bugzilla:
          1234561
          1234567
          1234562
      """
      assert True

So here in the ``Bugzilla`` docblock, in addition to the two BZs listed in the test case's
metadata, there is an additional ``BZ 1234562`` which is tangentially related to the test
case. These additional BZs could be in another focus area, but your test case happens to
hit them. They can be useful to someone trying to debug a failing test case.
