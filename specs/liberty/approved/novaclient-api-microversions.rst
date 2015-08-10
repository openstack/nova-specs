..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Nova API Microversions support in python-novaclient
===================================================

https://blueprints.launchpad.net/python-novaclient/+spec/api-microversion-support

The purpose of this spec is to call out the specific behaviour between
Nova and python-novaclient that is required now that we are using
microversions, and to provide guidance how other clients may wish to
interact with Nova.

Problem description
===================
As a community we are really good at evolving interfaces and code over time
via incremental development. We've been less good at giant big bang drops of
code. The Nova API is under heavy development, and we want to ensure that
consumers of Nova's API are able to make use of new features as they become
available, while also ensuring they don't break due to incompatibilities.

Microversions are implemented in the API through the addition of a new HTTP
header - specifically 'X-OpenStack-Nova-API-Version'.  This header is
accepted by Nova so a client can indicate which version of the API it wants
to use for communication, and likewise for Nova to indicate which version
it is using for communication.

For Nova API, if no HTTP header is supplied, v2.1 (stable/kilo) of the API is
used. If an invalid version is specified in the HTTP header, an HTTP 406 Not
Acceptable is returned. If the special 'latest' version is specified, Nova
will use its most recent version.

During changes being made to python-novaclient[1] to support Nova's
microversions it was discovered that there isn't a formal specification of how
Nova and a client should interact for varying cases of microversion mismatch
or for an unknown/unspecified microversion.

The need for this spec was discussed in liberty design session
"Nova: Nova API v2.1 in Liberty"[2].

Use Cases
---------

To address the specific behaviour between Nova and python-novacclient, the
following Use Cases are listed to specify the expected functionality.

For the purposes of definition, we will use the term "Nova V2.0" to refer to
a version of Nova that predates microversions and has no knowledge of them.
Likewise, we will use the term "Nova V2.1" to refer to a version of Nova
that includes support for microversions.

For novaclient, we will apply labels "old client" for novaclient which doesn't
support microversions and "new client" for novaclient which support it.

Use Case 1: Old Client communicating with Nova V2.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is exactly the same behaviour that was seen prior to the introduction
of microversions - no change to either the client or server is required
for this case.

* The client makes a connection to Nova, not specifying the HTTP header
  X-OpenStack-Nova-API-Version
* Nova does not check for an X-OpenStack-Nova-API-Version header, and
  processes all communication simply as v2.0 (stable/kilo)


Use Case 2: Old Client communicating with Nova V2.1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is where Nova is updated to a new version that support microversions,
but an old client is used to communicate to it.

* The client makes a connection to Nova, not specifying the HTTP header
  X-OpenStack-Nova-API-Version
* Nova does not see the X-OpenStack-Nova-API-Version HTTP header
* If Nova supports 2.1 microversion, which is equal to v2.0 (stable/kilo) of
  the REST API, Nova makes all communications with the client use that version
  of the interface. If microversion 2.1 support is dropped, Nova will return
  a proper exception, which the client should show to the user.


Use Case 3A: New Client communicating with Nova V2.0 (not user-specified)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[cli specific use case]
This is the where the user does not request a particular microversion to a
new client that support microversions and tries to communicate with an old
Nova.

* The user does not specify the microversion to use in communication with
  the client.  Consequently, the client attempts to use the latest
  microversion.
* The client makes a connection to Nova and ask supported API versions.
* Nova doesn't look for, or parse the HTTP header. It just return json with
  API versions [3].
* The client checks versions info and chooses 2.0 to use (until 2.1
  microversion is supported by new client) or informs the user that it cannot
  communicate to Nova using microversion and exits.

Use Case 3B: New Client communicating with Nova V2.0 (user-specified)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the where the user requests a particular microversion to a
new client that support microversions and tries to communicate with Nova V2.0.

From CLI:

* The user specifies a microversion that is valid for the client.
* The client makes a connection to Nova and asks for supported API versions.
* Nova doesn't look for, or parse the HTTP header. It just returns json with
  API versions [3].
* The client checks version info and informs the user that it cannot
  communicate to Nova using the requested microversion and exits.

From python code (BE CAREFUL):

* The user specifies a microversion that is valid for the client.
* The client attempts to make a connection to Nova.
* Nova doesn't look for or parse the HTTP header.  It just processes the call
  and returns a response with the results and without the HTTP header.
* The client doesn't check that the header is missing; the request has already
  been processed, so there is no reason to do so.

Use Case 3C: New Client communicating with Nova V2.0 (backward-compatibility)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the way to use Nova V2.0 via new client.

* The user specifies a compute api version to "2.0".
* [cli specific step] The client makes a connection to Nova and asks for
  supported API versions.
* The client makes a connection to Nova V2.0, without adding a
  X-OpenStack-Nova-API-Version HTTP header.
* Nova doesn't look for, or parse the HTTP header. It communicates using
  the only API code path it knows about, that being v2.0.
* The client doesn't look for, or parse the HTTP header, it knows that
  microversions doesn't used.
* The client processes received data, display it to user and exits.

Another supported way (CLI-only):

* The user specifies a compute api version to "None".
* The client uses default major version(2.0 for now).
* The client applies steps from the previous use case beginning from version
  negotiation.


Use Case 4: New Client, user specifying an invalid version number
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the case where a user provides as input to a new client an invalid
microversion identifier, such as 'spam', 'l33t', or '1.2.3.4.5'.

* The user specifies a microversion to the client that is invalid.
* The client returns an error to the user, i.e. the client should provide
   some validation that a valid microversion identifier is provided.

A valid microversion identifier must comply with the following regex:

  ^([1-9]\d*)\.([1-9]\d*|0|latest)$

Examples of valid microversion identifier: '2.1', '2.10', '2.latest', '2.0'...


Use Case 5: New Client/Nova V2.1: Unsupported Nova version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the case where a new client requests a version that is older than the
Nova V2.1 can handle. For example, the client supports microversions
2.1 to 2.6, and Nova supports versions 2.8 to 2.15.

From CLI:

* The user specifies a compute api version of "2.6".
* The client makes a connection to Nova and asks for supported API versions.
* Nova doesn't look for or parse the HTTP header. It just returns json with the
  API versions [3].
* As the client does not support a version supported by Nova, it cannot
  continue and reports such to the user.

From python code:

* The user specifies a compute api version of "2.6".
* The client makes a connection to Nova, supplying 2.6 as the requested
  microversion.
* Nova responds with a 406 Not Acceptable.
* As the client does not support a version supported by Nova, it cannot
  continue and reports such to the user.
* (An alternative path would be for the client to try and proceed using a
  version acceptable to Nova. Note that in this case the client should be
  able to proceed since any change that would break basic compatibility
  would likely require a major version bump to v3)


Use Case 6: New Client/Nova V2.1: Unsupported Client version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the case where a new client requests a version that is newer than
the Nova V2.1 can handle.  For example, the client supports microversions
2.10 to 2.15, and Nova supports versions 2.1 to 2.5.

Steps are the same as Use Case 5.

This scenario should not occur in practice as the client should always
be able to talk to any version of Nova.


Use Case 7: New Client/Nova V2.1: Compatible Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the case where a new client requests a version that is supported
by Nova V2.1. For example, the client supports microversions 2.8 to 2.10, and
Nova supports versions 2.1 to 2.12.

* [cli specific step] The client makes a connection to Nova and asks for
  supported API versions.
* The client makes a connection to Nova, supplying 2.10 as the requested
  microversion.
* As Nova can support this microversion, it responds by sending back a
  response with 2.10 in the X-OpenStack-Nova-API-Version HTTP header.


Use Case 8: New Client/Nova V2.1: Version request of 'latest'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[cli specific use case]
This is the case where a new client requests a version of 'latest' from a
Nova V2.1.

* The user specify 'latest' microversion to use.
* The client makes a connection to Nova and asks for supported API versions.
* Nova doesn't look for, or parse the HTTP header. It just return json with
  API versions[3].
* The client checks API version info and makes conclusion that current version
  supports microversions.
* The client chooses the latest version supported both by client and server
  sides(via "version" and "min_version" values from API version response) and
  makes a connection to Nova, supplying selected version in the
  X-OpenStack-Nova-API-Version HTTP header

Project Priority
----------------
V2.1 API [4]

Proposed change
===============
The python compute API in novaclient should be extended to
include major and minor parts of version. It should look like:

* "X.Y" - "X" and "Y" accept numeric values. The client will use it to
  communicate with Nova-API.
* "X.latest" - "X" accepts numeric values. The client will use the "latest"(see
  `latest-microversion`_ for more details) supported both by client and server
  sides microversion of "X" Major version.
* "latest" - The client will use the latest major version known by client and
  "latest"(`latest-microversion`_) microversion supported both by client and
  server sides.

   "X" is a major part and "Y" is a minor one

The requested microversion (when it specified) should be used (unless
the client cannot support that version). The client will always
request a specific microversion in its communication with the
server. 'X.latest' is purely a signal from a python consumer that it
wants negotiation of the maximum mutually-supported version between
the server and client.

python-novaclient as CLI tool
-----------------------------
Microversions should be specified with major API version.
Complete API version should be transmitted to python-novaclient via
compute-api-version option. Such way is backward compatible. Also users still
have ability to specify only major part of version.

The validation of compute api version(check format) should be done at first
step of python-novaclient(correct api version is needed to include correct
extensions, use correct command parsers and etc).

If user specify compute-api-version as 'None'(it means
--os-compute-api-version="None", which is different from not-specified
compute-api-version), client should use default major API version without
microversion.

Help message should display all variations of commands, sub-commands and their
options with information about supported versions(min and max).

Since cloud can have several service catalog entries of Nova API(v2, v2.1), it
would be nice to mention here:

* ``nova version-list`` cmd displays all entry points and supported
  microversions(min and max);
* Default service type, which is used to discover entry point to Nova API, is
  "compute". To choose correct entry point, user should use 'service-type' cli
  option.

Checked version should be transmitted to ``novaclient.client.Client`` function.

.. _latest-microversion:

"latest" microversion
~~~~~~~~~~~~~~~~~~~~~
"latest" microversion is the maximum version. Despite the fact that Nova-API
accepts the value of "latest" in the header, the client doesn't use this
approach. The client discovers the "latest" microversion supported by both
the API and the client, and uses it in communication with Nova-API.

Discovery should proceed as follows:

* The client makes one extra call to Nova API - list all versions[3];
* The client determines the current version by comparing the API response and
  the endpoint URL;
* The client checks that the current version supports microversions by checking
  the values "min_version" and "version" of the current version.
  If the current version doesn't support microversions ("min_version" and
  "version" are empty), the client uses the default major version (2.0).
* The client chooses the latest microversion supported by both novaclient and
  the Nova API.

.. note :: The "latest" version is supported only by the CLI. For version
   discovery while using python-novaclient as a library, use the
   ``novaclient.api_versions.discover_version()`` method.

Default Version
~~~~~~~~~~~~~~~
The default microversion should be changed to 'latest'. The goal of this
requirement is for python-novaclient / Nova communication to "just work" for
the user, and if possible, to use the most recent version of the REST API
possible, so that the user is able to make use of the latest functionality.

NOTE: this requirement is True only for python-novaclient as CLI tool, because
python-novaclient as a lib doesn't have default version and should not have it.

python-novaclient as a Python lib (novaclient.client entry point)
-----------------------------------------------------------------
Module ``novaclient.client`` is used as entry point to python-novaclient inside
other python libraries. The interface of this module should not be changed to
support backward compatibility.

``novaclient.client.Client`` function should accept a string value (the format
of version should be checked)[backward compatibility] or instance of
APIVersion object as a first argument.

python-novaclient should have a public way to check format of version to
simplify integration with other libraries.

If microversion(minor part of APIVersion) is specified, client should add
special header X-OpenStack-Nova-API-Version to each call and validate response
includes equal header too, which means API side supports microversions.

python-novaclient from developer side of view : adding new microverions
-----------------------------------------------------------------------
The variables ``novaclient.API_MIN_VERSION`` and ``novaclient.API_MAX_VERSION``
should be updated each time a new microversion is added or an old one is
removed.

Each "versioned" method of ResourceManager should be labeled with specific
decorator. The decorator accepts two arguments: start version and end
version (optional). Example:

.. code-block:: python

  from novaclient import api_versions
  from novaclient import base

  class SomeResourceManager(base.Manager)
      @api_versions.wraps(min_version='2.0')
      def show(self, req, id):
          pass

      @api_versions.wraps(start_version='2.2', end_version='2.8')
      def show(self, req, id):
          pass

      @api_versions.wraps(start_version='2.9')
      def show(self, req, id):
          pass

"versioned" commands should be labeled with decorator the same way as
ResourceManager's methods. ``@api_versions.wraps()`` decorator should be placed
before or after the CLI arg decorators. Example:

.. code-block:: python

  from novaclient import api_versions
  from novaclient.openstack.common import cliutils

  @api_versions.wraps("2.0")
  @cliutils.arg("name", help="Name of the something")
  @cliutils.arg("action", help="Some action")
  def do_some_show(cs, args):
      pass

  @cliutils.arg("name", help="Name of the something")
  @cliutils.arg("action", help="Some action")
  @api_versions.wraps(start_version='2.2', end_version='2.8')
  def do_some_show(cs, args):
      pass

  @api_versions.wraps(start_version='2.9')
  def do_some_show(cs, args):
      pass

"versioned" arguments should be used in such way:

.. code-block:: python

  from novaclient.openstack.common import cliutils

  @cliutils.arg('name', metavar='<name>', help='Name of thing.')
  @cliutils.arg(
      '--some-option',
      metavar='<some_option>',
      help='Some option.',
      start_version="2.2")
  @cliutils.arg(
      '--another-option',
      metavar='<another_option>',
      help='Another option.',
      start_version="2.2",
      end_version="2.9")
  def do_something(cs, args):
      pass

The example of implementation 2.2 microversion you can find here[5].

Alternatives
------------
One alternative to microversions is to not have them at all. What this would
result in would be a group of large changes happening simultaneously, resulting
in unpaired server/client versions not being compatible at all. It would also
result in less frequent, but larger incompatible API changes. And nobody wants
that.

Data model impact
-----------------
None. This change is isolated to the API code.

REST API impact
---------------
As described above, a new HTTP header would be accepted, and returned by
Nova.

If a client chose to use that header to request a specific version, Nova
would respond, either accepting the requested version for future communication,
or rejecting that version request as not being supportable.

If a client chooses not to use that header, Nova would assume that the REST API
to be used would be v2.1 (that is, the same API that was present in the 'Kilo'
release). This is how the REST API works today.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
Clients that wish to use new features available over the REST API added since
the 'Kilo' release will need to start using this HTTP header.  The fact that
new features will only be added in new versions will encourage them to do so.

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
Any future changes to Nova's REST API (whether that be in the request or
any response) *must* result in a microversion update, and guarded in the code
appropriately.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
::

  andreykurilin - Andrey Kurilin <andr.kurilin@gmail.com>
  xuhj - Alex Xu <hejie.xu@intel.com>

Work Items
----------
Complete the python-novaclient microversion implementation by:
    #. Chain of patches started from https://review.openstack.org/#/c/152569

Dependencies
============
None

Testing
=======
NovaClient's functional tests should cover as much as possible microverions.
Patch for V2.2[5] can be used as how-to for writing such tests.

Documentation Impact
====================
No specific documentation impact is identified that is not covered by existing
API change processes.

References
==========

* [0] http://specs.openstack.org/openstack/nova-specs/specs/kilo/implemented/api-microversions.html

* [1] https://review.openstack.org/#/c/152569/

* [2] https://etherpad.openstack.org/p/YVR-nova-api-2.1-in-liberty http://libertydesignsummit.sched.org/event/60da58ea4c57a2f25b2e1ed22213d6ce#.VXA9krxZ5Qt

* [3] https://github.com/openstack/nova/blob/master/doc/api_samples/versions/versions-get-resp.json

* [4] http://specs.openstack.org/openstack/nova-specs/priorities/liberty-priorities.html#v2-1-api

* [5] https://review.openstack.org/#/c/136458/
