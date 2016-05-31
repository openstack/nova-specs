..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Fix ConsoleAuthTokens API
==========================================

https://blueprints.launchpad.net/nova/+spec/fix-console-auth-tokens

The current ConsoleAuthTokens API allows getting connection info only for
tokens which correspond to RDP consoles. We need this API to also work for MKS
tokens in order to implement a standalone MKS proxy. The proposal is to change
this API to work for all types of tokens.

Problem description
===================

Standalone console proxies need this API but it is restricted only for RDP.
So there is no way to implement a console proxy outside of the Nova tree.

Use Cases
----------

Provide VM consoles for all protocols.

Project Priority
-----------------

N/A

Proposed change
===============

Change the implementation of ConsoleAuthTokens to provide connect
information for all types of tokens (not only RDP).

Alternatives
------------

The alternative is to put all proxy implementations in the Nova codebase.
This won't work for many reasons.

Data model impact
-----------------

None

REST API impact
---------------

The REST API will remain unchanged, only the implemenation will be changed. It
is as simple as removing the following if statement in console_auth_tokens.py::

    class ConsoleAuthTokensController(wsgi.Controller):
        def show(self, req, id):
            ...
            if console_type != "rdp-html5":
                raise webob.exc.HTTPUnauthorized()
            ...

However, we will need a new API micro version to differentiate from the old
behavior which is to return HTTP 401 for non-RDP tokens.

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
  rgerganov

Work Items
----------

It will be implemented in a single patch which fixes the API implementation
and bumps the micro version.

Dependencies
============

None

Testing
=======

Unit and functional tests.

Documentation Impact
====================

None

References
==========

History
=======

