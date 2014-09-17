..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support subclassing objects
==========================================

https://blueprints.launchpad.net/nova/+spec/object-subclassing

Implement support for subclassing objects properly. If some hook, extension,
or alternative DB API backend subclasses one of the base objects, the new
object should be registered and all code should end up using this new class.

Problem description
===================

Subclassing objects may be necessary to implement alternative DB API backends.
There are probably some other use cases where it may be necessary to override
some default object behavior. There was a rough plan to support subclassing
objects in trunk. However, it wasn't fully thought through before we started
landing all of the current object code. All objects do get registered right
now, however there is no checking of the versions the objects advertise.
Additionally, all code directly references the base object classes under
nova/objects right now.

Proposed change
===============

As objects are registered, check the version to see if it already exists. If
so, replace the original in the tracked object list with the new one. As
objects are registered, set an attribute on the nova.objects module to point
to the newest class for latest version of the object. Replace all code that
directly references object classes in modules under nova/objects with code
that uses the nova.objects attribute. This has a side-effect of cleaning up
imports. Instead of importing a ton of nova.object modules, only nova.objects
will be imported.

NOTE: This spec does not cover adding a hook/entrypoint for allowing
alternative object implementations. That will be proposed at some point as
a separate spec. At the moment, someone could specify an alternative db_backend
and register alternative object implementations that way, but I don't see that
as being the correct way to do that in the longer term.

Alternatives
------------

There are probably some alternatives to setting attributes on the nova.objects
module, like creating a method that returns the newest object and calling to
that method everywhere. That would result in slightly lower performance. I
suppose another solution to avoid having to change code everywhere is to
rename all object classes to Base<Object> and then somehow setattr the latest
version to be <Object> on the current modules. But, I rather like how using
objects.<Object> everywhere will look.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

The changes will touch a lot of files. Anywhere there is a reference to
something like instance_obj.Instance, it will change to objects.Instance.
There's high chance of conflicts to resolve in either the object-subclassing
patches or in other patches up for review.

New patchsets should never import the module defining an object to reference
the object class in it, directly. One should always import nova.objects and use
nova.objects.<Object>.

Objects register themselves when the module that defines them is imported.
With this change, since there's likely no need to import object modules in
code that uses them (you'll import nova.objects, instead), you must make sure
that object modules are imported within nova/objects/__init__.py's
register_all() method.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cbehrens

Work Items
----------

* Fix object registration to track object classes properly and set attributes
  on the nova.objects module
* Switch code to use the nova.objects module. This will be broken up into
  areas of nova like nova/api and nova/compute, etc.

Dependencies
============

None.

Testing
=======

Tests will be modified to use nova.objects as well.

Documentation Impact
====================

None.

References
==========

None.
