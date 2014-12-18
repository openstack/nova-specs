..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
i18n Lazy Translation Enablement for Nova
==========================================

https://blueprints.launchpad.net/nova/+spec/i18n-enablement-juno

This BluePrint/Spec proposes completing the enablement of i18n
(internationalization) support for Nova by turning on the "lazy" translation
support from the oslo.i18n library and completion of updating Nova to adhere
to the restrictions this adds to translatable strings.

Internationalization implementation has been an on-going effort in OpenStack
during recent releases.  The original blueprint for the Oslo support was
included in Havana:
https://blueprints.launchpad.net/oslo/+spec/delayed-message-translation

Blueprints for this support in Nova have been approved and worked on in
previous releases
(https://blueprints.launchpad.net/nova/+spec/user-locale-api).
During the Icehouse release, the foundational support for internationalization
was merged into Nova.  Specifically the update of Oslo's gettextutils and the
pre-existing work of explicitly importing '_' from gettextutils.

During the Juno release, hacking checks were added to restrict how
translatable messages are used in Nova.  In particular, ensuring that
translatable messages are not concatenated and that str() is not used on
exceptions.  Also Nova moved to using the oslo.i18n library.

To finalize this work in Kilo we need to enable the "lazy" translation
provided in the oslo.i18n library and fix a few cases where str()
is used on a translatable message.

Enablement of lazy translation will allow end users to not only have logs
produced in multiple languages, but adds the ability for REST API messages
to also be returned in the language chosen by the user.  This functionality
is important to support the use of OpenStack by the international community.


Problem description
===================

Today all users of Nova must agree on a common locale to use to translate
messages.  This is because messages are translated when they are created.
There is a need for different Nova users to be able to use different
translations simultaneously.

A user expects to be able to use Accept-Language in the header of a REST
API request to specify the locale they want responses translated and when
it does not match the locale used on the server.

Use Cases
---------
As a non-English speaking user, I'd like to make nova-api requests and get
the responses back in my native language.

Project Priority
----------------
None

Note that it needs to be enabled as early as possible to provide as much
'burn in' time as possible.  Also, lazy translation is currently in the
other projects.

Proposed change
===============

This proposal is to use the oslo.i18n library support in order
to enable "lazy" translation of messages.  This support, instead of
immediately translating the messages, creates a Message object which
holds the message and replacement text until the message can be translated
using the locale associated with the Accept-Language Header from the
user request.

The code changes will be done as a series of patches.

The first patch will add an enable_lazy() helper method (which calls
oslo.i18n's enable_lazy()) to nova/i18n.py that is controlled by a
temporary Nova configuration option 'i18n_enable_lazy' which is defaulted
to False.  A call to this new helper in nova/cmd/__init__.py.  Also
removal of the two remaining cases where str() is being called on
translatable messages.

The second patch will be to add an non-voting experimental tempest test which
sets this new configuration value to True and runs the tests.  Note that as an
experimental tempest test, this test will not be run for every commit.

The third patch will be to add a specific functional test that validates
that lazy enablement is working for Nova.

The fourth patch, would change the default value for the
configuration to True.   We would not remove the configuration
support until the next release.

The fifth and final patch would be to remove the non-voting experimental
tempest test added with the second patch.

Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

There is no additional changes to the REST API other than the fact
that the change will allow the API to correctly respond when the user
to specify the language they wish REST API responses to be returned in
using the Accept-Language option.

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

Once merged this feature is immediately available to users.


Developer impact
----------------

The developer impacts have already been in place for some time.  Developers
have been using _() around messages that need translation.

Since Juno developers have to adhere to the following hacking checks to ensure
enabling lazy translation will not cause failures:

* str() cannot be used on exceptions

* translatable strings cannot be concatenated

* replacement text cannot be specified using just locals()

* replacement text cannot be specified using just self.__dict__

A new hacking check in Kilo was added:
* unicode() cannot be used on exceptions being used as replacement text
https://review.openstack.org/#/c/129473/

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <jecarey@us.ibm.com>

Work Items
----------

Patch one

* Add enable_lazy() helper to nova/i18n.py with configuration control
  and defaulted to False (not using lazy translation)

* Add call to helper in nova/cmd/__init__.py

* Remove use of str() on translatable messages

Patch two

* Add non-voting experimental tempest test case configured to use
  lazy translation

Patch three

* Add functional test to Nova for lazy enablement

Patch four

* Change configuration control default to True (use lazy translation)

Patch five

* Remove non-voting experimental tempest test case added by patch two

Dependencies
============

This depends on version 0.6.0 or newer of the oslo.vmware library
which contains
https://review.openstack.org/#/c/122193/
which fixes lazy enablement support.  Nova currently requires at least
this version.

In order to prevent incorrect translations when lazy translation is
enabled, this spec depends on removing use of unicode() on exceptions
used as replacement text which was fixed under bug
https://bugs.launchpad.net/nova/+bug/1380806.


Testing
=======

* There will be a Nova functional tests added that will ensure that
  lazy translation is working properly.

  In order to make these tests less brittle, they will create a temporary
  translation (language) that is identical to the default translation
  (language) except that each translation will have a uuid prepended to
  the translation.  In this way lazy translation can be confirmed simply
  by checking for the presence of the uuid.

  - The first functional test will consist of running the server create API
    with and without lazy translation enabled and ensuring that the returned
    message is lazily translated.   This will be done by using Accept-Language
    in the request to requesting that the temporary language be returned and
    checking that the returned message includes the uuid.  Also, the request
    will be done without using Accept-Language and the absence of the uuid
    will be confirmed.

  - The second functional test will also consist of running the server create
    API, but in this case a second translation of the logs will be configured
    to translate the logs into both the original and temporary language.
    The logs will then be compared to ensure that, excluding debug logs, the
    logs only differ by the addition of the uuid in the ones translated with
    the temporary language.

* The hacking checks listed under Developer Impacts above.


Documentation Impact
====================

Need to ensure that the API documentation correctly indicates that the
Accept-Language option will now be used.


References
==========

* Accept-Language header: http://www.w3.org/International/questions/qa-accept-lang-locale
