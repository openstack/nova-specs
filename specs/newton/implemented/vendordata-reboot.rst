..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
vendordata reboot
=================

https://blueprints.launchpad.net/nova/+spec/vendordata-reboot

The nova team would like to stop dynamically loading python modules to
implement vendordata in the metadata service and configdrive. Instead, we
propose to provide a module which can fetch dynamic vendordata from an
external REST server.

Problem description
===================

Nova presents configuration information to instances it starts via a mechanism
called metadata. This metadata is made available via either a configdrive, or
the metadata service. These mechanisms are widely used via helpers such as
cloud-init to specify things like the root password the instance should use.

Nova currently supports a mechanism within metadata to add "vendordata" to the
metadata handed to instances. vendordata is currently supplied by a single
module, which is "plugged in" to metadata server via a flag which is a path to
a python module. There is currently only one implementation in the nova source
code, which takes a static JSON file and adds it to the metadata.

The nova team is concerned by this mechanism for plugging in vendordata
extensions because the python interface used is not stable, and if we change
the arguments to the call we don't know what external users we will break.
Additionally, running out of tree code in our processes is not preferred for
security reasons.

Instead, the nova team proposes to change the vendordata support to only load
_named_ modules, which must appear in the nova source code. We will provide a
module which is capable of making a REST call to an external service to fetch
vendordata, and a sample implementation of that external service for deployers
to extend.

Why can't this dynamic vendordata be supplied via user data during the boot
request? Sometimes this information isn't known at boot time, or isn't
something the end user of the instance can reasonably be expected to know. An
example is the cryptographic elements required to register the instance with
Active Directory, which the end user probably doesn't have the permissions to
generate.

Use Cases
---------

Static vendordata is useful when a deployer would like to specify things which
are always true about their cloud, but not expressable in the traditional
metadata. An example might be the IP address of their corporate LDAP servers.

Dynamic vendordata is useful for information which is specific to a given
instance, but not expressable via the metadata schema. An example might be the
cryptographic elements required for the instance to register itself with an
Active Directory implementation post boot.

Proposed change
===============

* Deprecate loading python modules for vendordata. Do not remove this support
  just yet though. This is already done.

* Add a new flag, vendordata_providers, which is a list of the names of
  modules which add vendordata to the instance metadata. The current
  vendordata_json module will be be presented as "StaticJSON" in this list.

* Add a new module which hooks the name "DynamicJSON" and which has a flag to
  configure a list of URLs to REST microservices which provide dynamic
  metadata.

We need to make sure that the module which implements DynamicJSON does
something sensible with the HTTP caching headers from the REST microservices.
These can be used to manage a cache on the nova side to reduce the load on the
microservice from repeated requests as much as possible. Additionally, SSL
verification for REST microservices might need to be different from that we
use for other services, as these services are likely to be internal only and
using self signed certificates. This behaviour should be controlled by a flag.

DynamicJSON also needs to implement a HTTP request timeout in case the REST
microservice does not answer in a reasonable amount of time. In this case
vendordata is created without the entry from that microservice (in other
words, no key at all in the examples below), and instance spawn continues.

What data do we pass to the REST microservice? It is currently believed that
we should provide the following attributes:

* Project ID
* Image ID
* Instance ID
* Any user-data that has been defined

This data will be sent as a JSON encoded POST to the REST microservice.

How do we handle adding new data to the set that is passed to the microservice?
I am sure that we will find in the future that there is additional data that
needs to be passed to microservices. This shouldn't be too bad though -- we can
add data to the set we pass, while removing data will be much harder.
Therefore, deployers can request additional data be passed as required, and as
long as they ensure they handle that data being missing until they upgrade
everything should work out ok.

How does the microservice know that a genuine request is being made by Nova? We
propose to pass on the token the caller to Nova gave us to the microservice
as part of our call, in the same manner that calls to Cinder, Glance or Neutron
are passed the client's token. This will allow the microservice to ensure that
the client is authorized to perform the action the microservice implements.
This has the implication that microservices will need to be able to implement
keystone authentication -- this is certainly the case for microservices written
in Python to use WSGI, who should be able to use the existing middleware. We
believe there are also keystone client implementations for Go and Java.

How do we handle metadata from multiple services? To remain backwards
compatible, any StaticJSON which is defined will appear in the metadata in a
file called vendor_data.json.

For DynamicJSON, the results of calls to the microservice will be placed into
a new JSON file in the metadata, called vendor_data2.json. This file contains
a dictionary which is a series of dictionaries. For example::

 {
     "static": {
         "bar": "2",
         "foo": "1"
     }
 }

In this example you can see that the static JSON is also included in this
new file, raising the hope that people will eventually only need to read one
file to get all of the vendordata. Each REST microservice is configured by
appending a new item to the list provided in the vendordata_dynamic_targets
flag. This flag is composed of entries of the form:

 name@http://example.com/foo

The name element for this microservice becomes the a new key for the
vendor_data2.json file, like this::

 {
     "name": {
         "fancy": "pants"
     },
     "static": {
         "bar": "2",
         "foo": "1"
     }
 }

It is assumed that the deployer will ensure that a name only appears for one
microservice. Duplicated names will be handled as a run time error which
stops the instance from spawning.

If a REST call returns {}, then an empty entry in vendor_data2.json is made.

Alternatives
------------

It was proposed that we could instead implement things like dynamic vendordata
using user-data that is added to a user's request by WSGI paste middleware
that captures the nova boot request from the user and adds extra data before
passing the request to nova-api. This is problematic for a few reasons:

* Its likely to be unreliable as its implementation is not particularly
  obvious to a newcomer.

* That code would run in a nova process, which is undesirable.

* User data is stored in the nova database, which is undesirable for
  cryptographic data.

* I was told that this proposal was the most hacky thing Sean Dague had ever
  heard of, and that he had to take a valium before he could continue the
  conversation. I found this mildly offensive. It has therefore been shown
  that implementing this functionality via middleware is likely to hurt nova
  core's feelings and we can't have that.

Data model impact
-----------------

None

REST API impact
---------------

None for the nova REST APIs. There will be a new, very small, API for the
external REST server, but this is considered a minor issue.

Security impact
---------------

We wont be storing confidential information in the nova database any more, as
we do if people use user-data for equivalent functionality. Additionally,
no nova process needs priviledged access to any corporate system, as that is
handed off to the REST microservice. This reduces the surface area that a
corporate system admin needs to worry about securing.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

There is a risk that the external REST microservice for dynamic vendordata
might be down or very slow when the request is made. We can use a timeout to
ensure the nova boot process isn't heavily degraded. This might result in
instances lacking all the data they need to be useful once booted, but this is
outside the control of nova.

Some metadata server users make requests for metadata very frequently, and
this could cause the external REST service to experience heavy load. However,
the deployer of that microservice can use techniques such as caching and load
balancing to alleviate these problems. Nova will also implement handling of
the HTTP caching headers in the responses from the REST service to try and
reduce the number of times we need to call out to the REST service.

Other deployer impact
---------------------

For deployers using dynamic vendordata, they will need to maintain another
REST service.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mikal

Other contributors:
  None

Work Items
----------

* Write the nova support for this functionality.

* Provide a sample external REST microservice, possibly not in the nova source
  tree.

* Add testing support to devstack / tempest.


Dependencies
============

None


Testing
=======

We should test this functionality by adding the sample REST microservice to
devstack, and add at least one tempest test which verifies that this all works
end to end.

Documentation Impact
====================

The admin guide will need to be extended to explain this functionality.

References
==========

This work was prompted by discussions at the Newton design summit in sunny
Austin, as well as the openstack-operators thread at:

 http://lists.openstack.org/pipermail/openstack-operators/2016-April/010179.html

History
=======

None
