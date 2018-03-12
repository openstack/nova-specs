..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Convert Consoles To Use Objects Framework
=========================================

https://blueprints.launchpad.net/nova/+spec/convert-consoles-to-objects

Make consoles to use the objects framework -- the current console code
does not take advantage of the framework objects, instead it provides
some types (console/type.py) to handle them. These types do not
provide any features to handle versioning, RPC or any kind of methods
to make them useful.


Problem description
===================

The current code does not provide any mechanism to handle versioning.
Additionally, since RPC cannot handle classes derived from the Python object
type, we need to handle a dict "connect_info" between RPC calls and no
way is provided to share the state of the console across processes.

Another problem comes with the token, memcached is not a database and
cannot guarantee that the expire time will be respected, a token can
expire before that limit (eviction). By using the framework objects
we can get the opportunity to store the whole state of Console object
with a valid token in the database and share the state between
process.

For instance bug 1425640 needs to know when an user is connected to a
particular port from a number of perspectives: from the compute node, to
return the next port defined and not connected; from the proxy to
reject new connections on already connected port from the API to
let user informed no more port are available.

We will also enhance security by only storing a hash of tokens in the
database after to have returned the clean one to the users. Then when
users will request to connect a console the token passed will be
hashed and compared to the one stored in the database for validation.

A new option will be introduced ``[workarounds]enable_consoleauth`` which will
allow operators to opt-in to enabling use of both the database and legacy
consoleauth backend at the same time. The use case for this is if the operator
does not want all of their already existing console authorizations to be
invalidated once the database backend is available. Usually, the TTL for
console authorizations is short-lived (default is 10 minutes) so invalidating
existing consoles should not be a problem in the usual case. However, if an
operator has configured much longer TTL, they may want to take advantage of the
``[workarounds]enable_consoleauth`` option to allow fall back to consoleauth
for already existing consoles. Once all pre-database-backend console
authorizations have expired, the operator may set
``[workarounds]enable_consoleauth`` back to False and stop running the
consoleauth service.

The consoleauth service will be retained for legacy compatibility but
in a deprecated status, supported for one release. After the
period the consoleauth service can be removed.

Because the new tokens will go in the database we need to consider
cells v2. The child cell database is the appropriate place for console
connection info because it relates directly to instances. Currently
the console connection URLs returned to the user only contain a token.
This is not sufficient to determine which cell holds the console
connection. An initial idea for handling this was to add the instance uuid to
the console proxy URL and use it to target the instance's cell database for the
verification of the origin protocol by the console proxy. However, when we
added the instance uuid to the URLs, the Tempest jobs failed on the noVNC tests
because noVNC was not able to separate more than one query parameter in the
URL, so the ``?instance_uuid=<uuid>`` portion of the URL was being considered
as part of the token, the first query parameter ``token=<token>``. So, instead
we will resolve the cell database issue by running console proxies per cell
instead of global to a deployment, such that the cell database is local
to the console proxy. This approach is backward compatible with the existing
console proxies and also decreases load on a large deployment by sharding
proxies per cell instead of all consoles for the deployment going through one
centralized proxy.

Use Cases
----------

Developer can take advantage of using the framework objects when
adding a new console or features.

Proposed change
===============

* Define a new ConsoleAuthToken object.
* Convert drivers to generate ConsoleAuthToken object.
* Define schema and API to store ConsoleAuthToken object in child cell
  database.
* Update code to store ConsoleAuthToken with valid token in database
  or consoleauth dependant on the switch until consoleauth is removed.
* Update proxies to use the database or consoleauth dependant on the
  switch until consoleauth is removed.
* Define a periodic task to clean expired object stored in database;
  To balance the load and avoid blocking the database during too much
  time each compute nodes will be responsible to clean connection_info
  for guests they host.
* Add a config option ``[workarounds]enable_consoleauth`` defaulting to
  False that operators can opt-in to if they wish to run the legacy
  consoleauth service to fall back on if they have configured long TTL
  for console authorizations and do not wish to have already existing
  consoles invalidated once the database backend is available.
* Update documentation to reflect the new required deployment layout
  where console proxies are run per cell.
* Fix bug 1425640

Alternatives
------------

Continue to use memcached as a backend will make the behavior of
connection information not previsible since objects can be
evicted. Also in order to fix issue 1425640 and 1455252 a scan has to
be done to list available ports which is difficult when using
memcached without add specific code to maintain a list of stored keys.

Data model impact
-----------------

A new ConsoleAuthToken model needs to be defined with attributes:

- instance: an instance which refer the console
- host: a string field to handle hostname
- port: an int field to handle service number
- token_hash: a string field to handle a token or null
- access_url: a string field to handle access or null
- options: a dict field to handle particular information like usetls,
  internal_access_path, mode...
- expires: a date time to indicate when the token expires or null

The database schema ::

    CREATE TABLE console_connection (
         instance_uuid CHAR(36) NOT NULL,
         host VARCHAR(255) NOT NULL,
         port INT NOT NULL,
         token_hash CHAR(40),
         access_url VARCHAR(255),
         options TEXT,
         expires DATETIME,

         PRIMARY KEY (instance_uuid, host, port),
         INDEX (token, instance_uuid),
         FOREIGN KEY (instance_uuid)
           REFERENCES instances(uuid)
           ON DELETE CASCADE
    );

.. note::

    No migration are expected from serialized dicts connection info
    stored in memcached to the database, during the upgrade clients
    already connected to consoles will keep their connections until
    proxy will be restarted. At this step we expect to have the
    consoleauth service to also have been restarted.

REST API impact
---------------

None

Security impact
---------------

In the point of view of tokens we can expect a better security since
currently tokens are stored in memcached which does not provide any
security layer. Now only hash of tokens will be stored in the database
also security policy will enhanced to be the same than other critical
components stored in database.

Notifications impact
--------------------

None

Other end user impact
---------------------

When proxyclient will be restartred users will be disconnected from
our consoles but should reconnect to it with the same token if not
already expired.

Performance Impact
------------------

The database load will increase but we can expect that with a minimal
impact for DBA.

Other deployer impact
---------------------

The consoleauth service must be restarted before proxy services. When
proxy will be restarted clients will be disconnected from consoles.
consoleauth will continue to work as backend until a deprecated period
of one release operator are encouraged to switch on the database
backend (see option: console_tokens_backend).

If the deployer choses to use the database to store console connection
information the consoleauth service will not be required.

Developer impact
----------------

None

Upgrade impact
--------------

New console token authorizations will be stored in the database but already
existing consoleauth service token authorizations will continue to work until
their TTLs expire, if the operator has set
[workarounds]enable_consoleauth = True before upgrading (the default is False).
Once all of the old consoleauth service token authorizations have expired, the
flag should be disabled and it will no longer be necessary to run the
consoleauth service.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  sahid-ferdjaoui

Work Items
----------

* Convert code to use objects framework
* Update consoleauth to take advantage of the database to handle
  tokens
* Fix bug 1425640

Dependencies
============

None

Testing
=======

The current code is already tested by functional and unit tests since
we do not provide any feature we can consider that the code will be
well covered by those tests.

The new version will be tested in the gate.

Documentation Impact
====================

The cell deployment layout documentation will be updated to reflect the new
requirement that console proxies must be run per cell instead of global to
a deployment.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Newton
     - Re-proposed
   * - Pike
     - Re-proposed
   * - Queens
     - Re-proposed
   * - Rocky
     - Re-proposed
