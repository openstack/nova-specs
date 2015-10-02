..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Adding Python 3.4 support to Nova
=================================

https://blueprints.launchpad.net/nova/+spec/nova-python3


Problem description
===================

It's time to add Python 3 support to Nova by generalizing the usage of the six
module, in addition to the Python 2 support.

Use Cases
----------

See the article `Why should OpenStack move to Python 3 right now?
<http://techs.enovance.com/6521/openstack_python3>`_ for the rationale.


Project Priority
-----------------

None


Proposed change
===============

This specification details the steps needed to add Python 3.4 support to Nova
by generalizing the usage of the six module.

Almost all Nova dependencies are ported to Python 3. For the few remaining
libraries, the port is in progress and should be done in a few weeks. It is
already possible to start porting Nova to Python 3. See the Dependencies
section below for more information.

The goal here is to make all Nova tests pass with Python 3: Nova unit tests and
Tempest tests.

.. note::
   Python 2 support is kept.


Alternatives
------------

None

Data model impact
-----------------

None (changes must not impact the data model).


REST API impact
---------------

None (changes must not impact the REST API).


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

There is no impact on performances.

In March 2013, Brett Canon ran `the official Python benchmarks suite
<https://hg.python.org/benchmarks>`_ to compare Python 2.7 and 3.3 for his talk
at Pycon US: `Python 3.3: Trust Me, It's Better Than Python 2.7
<https://speakerdeck.com/pyconslides/python-3-dot-3-trust-me-its-better-than-python-2-dot-7-by-dr-brett-cannon>`_.
The result: "If you sorted all of the benchmarks and looked at the median
result ... Python 3 is the same".

See the "Optimizations" section of each "What's New in Python 3.x" document for
the full list of optimizations: `Python 3.1
<https://docs.python.org/3/whatsnew/3.1.html#optimizations>`_, `Python 3.2
<https://docs.python.org/3/whatsnew/3.2.html#optimizations>`_, `Python 3.3
<https://docs.python.org/3/whatsnew/3.3.html#optimizations>`_ and `Python 3.4
<https://docs.python.org/3/whatsnew/3.4.html#significant-optimizations>`_.

Other deployer impact
---------------------

Deployers using python 2.7 will see no changes.

Those able to run python 3.4 will now be try that out.

Developer impact
----------------

Once the Python 3 check job becomes voting, developers will have to write code
compatible with Python 2 and Python 3. During the transition period, only code
tested by the ``tox.ini`` whitelists will require Python 3 support.

Thanks to tox, it is trivial to run locally the Nova test suite on Python
2.7 and 3.4.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  victor-stinner

Other contributors:
  None

Work Items
----------

* Fix most obvious Python 3 issues. Example of a patch fixing most Python 3
  issues: `Port Nova to Python 3
  <https://github.com/haypo/nova/commit/bad54bc2b278c7c7cb7fa6cc73d03c70138bd89d>`_.
  This change is just a draft to test if porting Nova is feasible, it
  should be splitted into smaller patches grouped by similar changes. See also
  the `Port Python 2 code to Python 3
  <https://wiki.openstack.org/wiki/Python3#Port_Python_2_code_to_Python_3>`_
  section of the Python 3 wiki page.

* Add a Python 3 test environment to ``tox.ini`` to run a subtest of the tests
  which pass on Python 3. It will use a whitelist of tests which are know to
  pass on Python 3.

* Add a non-voting Python 3 check job for Nova

* When the Python 3 check job is stable enough, make it voting. From this
  point, we should now be able to avoid Python 3 regressions while working.

* Fix failing tests, one by one, to enlarge the whitelist of tests
  in ``tox.ini``.

* Once all tests work, remove the whitelist of tests from ``tox.ini``.

The transition period, when Python 3 is only supported partially, should be a
short as possible.

No voting Python 3 gate jobs will be added to not waste resources of the
OpenStack infra, Python 2 gate jobs are enough. We consider that there is a low
risk of having a Python 3 specific issue introduced by a conflict between the
Python 3 check job and the Python 2 gate job.


Dependencies
============

Remaining dependencies not compatible with Python 3 yet:

* ``oslo.messaging``: The development version works on Python 3, except of Qpid
  and AMQP 1.0 drivers. To begin the Nova port to Python 3, we can start with
  the RabbitMQ driver, until AMQP is ported to Python 3 too. A new version
  of ``oslo.messaging`` will be released in a few weeks.
* ``mysql-python``: the fork `mysqlclient
  <https://pypi.python.org/pypi/mysqlclient>`_ works on Python 3 and includes
  bug fixes. There is also `PyMySQL <https://pypi.python.org/pypi/PyMySQL>`_,
  a driver fully implemented in Python which works on Python 3 too, but it has
  worse performances.
* ``python-memcached``: see the pull request `Port memcache to Python 3
  <https://github.com/linsomniac/python-memcached/pull/67>`_. It blocks
  ``keystonemiddleware``. It may be replaced with ``pymemcache`` which is
  already Python 3 compatible.
* ``websockify``: Python 3 classifier is missing in websockify 0.6.0, but it
  is present in the development version. Tests are failing but they may be
  issues with the tests, not with websockify directly.

All in all, there is no major issue with the dependencies.

Using the development version of ``oslo.messaging``, it's already possible to
work on fixing Nova tests on Python 3.


Testing
=======

The current test suite should be enough to test Nova on Python 3.

We will run tests with Nova running under Python 3.4 by the end of this
process: Nova unit tests and Tempest tests.


Documentation Impact
====================

Developers might be interested in reading the official `Python 3 page
<https://wiki.openstack.org/wiki/Python3>`_ on the Openstack wiki. It shows
the current progress of the OpenStack port of Python 3, and details some common
issues that arise when porting code from Python 2 to Python 3.


References
==========

* Related Liberty specifications:

  - Heat: `Add Python 3.4 support <https://review.openstack.org/#/c/175340/>`_
    by Sirushti Murugesan
  - Neutron: `Porting to Python 3 spec
    <https://review.openstack.org/#/c/172962/>`_ by Cyril Roelandt with the
    support of Ihar Hrachyshka.

* `Python 3 page in OpenStack wiki <https://wiki.openstack.org/wiki/Python3>`_


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
