..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Refactor network API
======================

https://blueprints.launchpad.net/nova/+spec/refactor-network-api

To have a common API network base with all required methods so
neutron / nova network api can inherit from.


Problem description
===================

Right now network api's do not inherit from a common base, and if the
functionality is not implemented developers may forget to add the
method.
The situation is that every time that functionality want to be accessed
from the API an exception is thrown due to missing methods and not clear
error is returned.

Proposed change
===============

The idea is to create a network_base API that define all the possible
methods and just throw NotImplementedError, so next time the user will
see the proper error message.

Also fields like sentinel object could be directly inherited in the base
api.

Alternatives
------------

The current way to do this is to manually add the missing methods to
neutronv2 api for instance. Every time someone add a new method to one
api has to do the same for the others and raise NotImplementedError if
not supported.

Data model impact
-----------------
None

REST API impact
---------------
None

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
None

Other deployer impact
---------------------
None

Developer impact
----------------

If developers add new methods to neutronv2 or nova-network api,
they must define it first on the new network base api.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  leandro-i-costantino

Work Items
----------

 * Create a base network api files that has all the public methods
   from current network api


Dependencies
============
None

Testing
=======
None

Documentation Impact
====================
None

References
==========
None
