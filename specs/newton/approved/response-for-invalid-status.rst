..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Return 400 When Bad Status Values are Received
==============================================

https://blueprints.launchpad.net/nova/+spec/response-for-invalid-status

A bug was found where passing an invalid status to the server listing API would
return an empty list for a regular user, but would raise an exception and
return a 500 error for admin users. That has since been fixed
(https://review.openstack.org/#/c/335648/), but in the discussions about that
bug it was felt that while fixing the exception was certainly correct, the list
of valid status values is small and well-defined, so returning an empty list
was not the desired behavior; instead, the user should get a 400 Bad Request
instead.


Problem description
===================

A bug was found when listing servers with a status filter that happened if an
invalid status value was passed: https://bugs.launchpad.net/nova/+bug/1579706.
It would only happen for admin users, because it would try to fetch extended
server attributes, and that code expected instances to be present in the cache,
and would throw a KeyError exception. While discussing that bug, though, it was
felt that the non-admin response (returning an empty list) was not correct,
either, since statuses are limited and well-documented, and an invalid status
was much more likely to be a typo (such as 'EROR' instead of 'ERROR'). The
correct response in this case should be a 400 Bad Request, so that the user
would be aware that they made a mistake, giving them the opportunity to correct
it.

Use Cases
---------

As a user, if I mistakenly ask the API to list servers with a status that does
not exist, I want to know that I did something wrong with my request, as it is
most likely a typo, and not an actual request for servers whose status is, say,
'ACTVIE', when I meant 'ACTIVE'.


Proposed change
===============

When a request to filter the list of servers by status is received, verify that
the status is one of the defined statuses for a server. If it is not, return a
400 Bad Request.

Alternatives
------------

We could just continue to treat all statuses as valid, and return an empty list
when an invalid status is passed, and let the user deal with the results.

Data model impact
-----------------

None

REST API impact
---------------

This is a change to the API, and will require a new microversion.

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

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <ed-leafe>

Other contributors:
  <Dinesh Bhor>

Work Items
----------

* Check any status passed to the list servers API is valid, and if not, return
  a 400 Bad Request.


Dependencies
============

None


Testing
=======

A new test will be added that verifies that an incorrect status in a server
list request will raise a 400 Bad Request.


Documentation Impact
====================

None. Users should not be expecting that incorrect statuses will work.

References
==========

Original Bug: https://bugs.launchpad.net/nova/+bug/1579706


History
=======
