..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add offset to console logs
==========================================

https://blueprints.launchpad.net/nova/+spec/console-log-offset

In order to observe console logs from specified position we need to add new
optional argument to console logs command that allows to list logs from
specified position.

Problem description
===================

When user triggers console-log command it gets all logs from the end.
It might be not useful to get all log content when you observe your system
activity and want to see logs about event that happened in the past. Scrolling
thousands of lines might be annoying.

Use Cases
---------

Operator wants to observe logs from specified offset.

Proposed change
===============

Additional optional parameter offset should be added to handle the problem
when operator want to show part of log.

Alternatives
------------

An alternative would be to show all log all or specified amount of lines from
tail and scroll up until you get what do you need.

Data model impact
-----------------

None

REST API impact
---------------

The proposal will add new optional parameter 'offset' for request.
This change will need bump in API microversion. In case of empty log or
if log doesn't contain this offset response should be empty.

Request:

   URL:
      /v2.1/​{tenant_id}​/servers/​{server_id}​/action

   Method:

      POST

   JSON format:

      {
         "os-getConsoleOutput": {
            "lines": 2,
            "offset": 10
          }
      }

   Response:

      {
         "output": "ANOTHER\nLAST LINE"
      }


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

python nova client will be updated with new optional parameter
to console-logs command. New command will looks like:

nova console-logs <instanced-id> --length 10 --offset 100

Performance Impact
------------------

Reduce amount of data transferred to python-novalcient.

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
  gstepanov

Work Items
----------

*  Update API microversion on getting console logs with offset parameter

*  Update python-novaclient API by adding offset parameter


Dependencies
============

None


Testing
=======

Would need new Tempest, functional and unit tests.


Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

None
