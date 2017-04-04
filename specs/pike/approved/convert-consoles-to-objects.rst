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

A new option will be introduced "console_tokens_backend" which will
allow operator to switch between different backends. The scope of this
spec will allow 2 backends: consoleauth (using memcached) or database.
The consoleauth service will be retained for legacy compatibility but
in a deprecated status, supported for one release. After the
period the consoleauth service can be removed.

Because the new tokens will go in the database we need to consider
cells v2. The child cell database is the appropriate place for console
connection info because it relates directly to instances. Currently
the console connection URLs returned to the user only contain a token.
This is not sufficient to determine which cell holds the console
connection. This can be resolved by adding the instance uuid to
the query string in the URL. This approach is backward compatible
with the existing console proxies. Ultimately it is still the
token that determines authority to connect to the console, but
we will add verification that the instance uuid in the URL matches the
instance uuid in the connection info retrieved for the token.

Use Cases
----------

Developer can take advantage of using the framework objects when
adding a new console or features.

Proposed change
===============

* Define a new ConsoleConnection object.
* Convert drivers to generate ConsoleConnection object.
* Define schema and API to store ConsoleConnection object in child cell
  database.
* Update code to store ConsoleConnection with valid token in database
  or consoleauth dependant on the switch until consoleauth is removed.
* Add the instance uuid to the console proxy URLs to allow proxies to
  locate the child cell database containing the connection info.
* Update proxies to use the database or consoleauth dependant on the
  switch until consoleauth is removed.
* Define a periodic task to clean expired object stored in database;
  To balance the load and avoid blocking the database during too much
  time each compute nodes will be responsible to clean connection_info
  for guests they host.
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

A new ConsoleConnection model needs to be defined with attributes:

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

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  PaulMurray

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

None

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
