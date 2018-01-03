Frequently Asked Questions
==========================

How do I increase logging level of the testing framework?
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""

You can put logging entry into your env.local.yaml like this:

.. code-block:: yaml

    logging:
        level: DEBUG

Can I run tests in interactive mode?
""""""""""""""""""""""""""""""""""""

Yes, you can. Just call IPython's method ``embed()`` wherever you need the execution
to enter an interactive mode. Example:

.. code-block:: python

    def test_foo(bar):
        x = do_something()
        from IPython import embed; embed()
        assert x

Then you can run your test with -s parameter: ``pytest -s cfme/tests/test_foo.py::test_foo``.
Once the execution reaches the "breakpoint", you will be presented with IPython's
interactive prompt.

Another way is to use the python debugger - `pdb <https://docs.python.org/2/library/pdb.html>`_.

.. code-block:: python

    def test_foo(bar):
        x = do_something()
        import pdb; pdb.set_trace()
        assert x


How do I build this documentation?
""""""""""""""""""""""""""""""""""
Go to cfme_tests/integration_tests/docs and run ``make clean && make html``.
Then go to _build/html. You can open and view the HTML files in your browser.