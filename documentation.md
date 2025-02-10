# Booking System Technical Summary

## Booking System Configuration
Static config is handled in the settings.py file, 'live' configuration
regarding the booking system is handled via snippets in the admin
menu. The configuration is heirarchy is:

```
+- Config
  |- Max weeks till booking
  |- Time of day rollover
  |- Number of rooms
  |- Week start day
  |- Flexible booking weeks
  |- Last minute booking weeks
  |- Maximum family members
w  +- Members
  |  |- Share number
  |  |- First name
  |  |- Last name
  |  |- Contact email
  |  |- Contact phone
  |  +- Family Members
  |    |- First name
  |    |- Last name
  |    |- Contact email
  |    |- Contact phone
  +- Room Types
  |  |- Double beds
  |  |- Bunk beds
  |  |- Last name
  |  |- Max occupants (automatically generated)
  |  +- Rooms
  |    |- Room number
  +- Seasons
     |- Season name
     |- Max monthly room weeks
     |- Max monthly simultaneous rooms
     |- Start month
     |- End month
     |- Season is peak
	 |- Requires strict weeks
     +- Booking Types
       |- Booking type name
       |- Rate
       |- Is full week only
	   |- Sets weekly rate cap
	   |- Requires flexible booking period
	   |- Requires last minute booking period
       |- Is flat rate
       |- Banned rooms
       |- Minimum Rooms
	   |- Priority
```
In the above list entries marked with a '|-' are configuration values
under the Snippet, while items markeed with '+-' are Snippets (in
django terms models, discrete bundles carrying configuration
information). Snippets connected by lines are linked by the
subordinate (child) snippet deriving some properties through
association with the parent snippet. For example, Family Members are
associated with a Member.

The Snippets are described below in order. Help text clarifies most
fields through the web interface; however, some instruction on the
underlying abstractions also follows:

- A 'Config' represents the state of the lodge and carries
 entire-lodge settings. Weeks are released for booking one at a time
 on a rolling basis at a certain time of day AEST (to avoid 12:01 am
 booking sniping) which most top level settings here refer to. Last
 minute bookings happen a certain number of weeks out (configured
 here) and if a booking ends within that period normal season rules
 are suspended.
- A 'Member' represents one share, and is associated with the
  shareholder. Member 0 is a dummy member that can be used when
  blocking out rooms for maintenance.
- A 'Family Member' is somebody authorised to use that share to book a
  stay. The person who is associated with the Member share is a Family
  Member of that share too.
- A 'Room Type' is a configuration a room can have in terms of number
  of beds. It automatically derives the maximum number of people who
  can stay according to the available beds.
- A 'Room' is a physical room in the lodge.
- A 'Season' is a range of months associated with a booking
  season. This does not have to line up with a calendar season but
  does need to start and end on a calendar month. A season can a 'peak
  season' in which case it can overlay another non-peak season and
  override the behaviour for the overlapping season. This is useful to
  avoid duplicating 'base' season config either side of a month of
  peak activity where additional restrictions or fees may
  apply. If a season `requires strict weeks` then for a booking to
  count as a weekly booking it must arrive on the `week start day` and
  depart on the `week start day`. Otherwise any contiguous seven-day
  period will use weekly rates.
- A 'Booking Type' is a valid sort of booking for the attached
  season. For example a daily rate applicable to some subset of
  rooms. A 'flat rate' is approprate if and only if the cost of the
  booking should not be multiplied by the number of rooms
  booked. Bookings which require flexible booking period can only be
  made inside that number of weeks. In a season one booking can be
  nominated to set the weekly rate cap, if this is set then if a
  number of days in a week would cost more than this booking they will
  instead be charged at the rate of this booking.
  
### NB

Currently (2025-02-10) validation methods for children of
`ClusterableModel`s is broken. You have a choice between a convenient
interface using the inline forms for child snippets such as
FamilyMembers or creating those directly via an inconvenient but safe
method. Make whatever choice you find appealing.

  
## Ongoing Management of Configuration

### Changing Member Associated with a Share

If a member transfers their share, or otherwise the details of the
member change then the `Member` details should be updated directly. In
order to preserve the integrity of the booking system `Members` cannot
be deleted once they have made a booking.

The full proceedure is to:

- Mark the User account as inactive.
- Delete the `Family Members` associated with the `Member`.
- Update the `Member` details and add the necessary `FamilyMembers`.
- Create or reactivate a User for the new member.
- Check the new user has a OTP device if reactivating them.

### Changing Season Dates

To avoid tripping validation first _shrink_ seasons so that there are
vacant months to expand into, then edit the appropriate season to
cover the now-vacant months.

## Booking Record Model

Booking are represented by Booking Records which have the following
structure:
```
+- BookingRecord
  |- Member
  |- member name at creation
  |- last updated
  |- arrival date
  |- departure date
  |- Rooms
  |- Member in Attendance
  |- member in attendance name at creation
  |- other attendees
  |- cost
  |- payment status
  |- paypal transaction id
  |- status
  |- reminder sent
  |- send admin email
```

Capitalised entries are relations to models defined in the
configuration (see [Booking System
Configuration](#booking-system-configuration)). Most fields are
documented via their helptext, some unusual features are explained
below:

- member name at creation and member in attendance (MIA) name at
  creation: Since a member might change in the future (and with them
  the MIA) these fields are automatically assigned when a
  BookingRecord is created for integrity of any records
- last updated: a field only shown in the inspector or on export, this
  marks when a record was last updated. It is used for expiring
  incomplete bookings and for record keeping
- other attendees: a JSON record of different people attending, mostly
  of interest if something goes wrong. The format is `{guest\_x:
  {first\_name: foo, last\_name: bar, email: baz@tux.com}, ..}` which
  is a relatively cursed format that doesn't display well but such is
  c'est la vi
- payment status: One of `IS (issued), PD (paid), FL (failed), RF
  (refunded), or NI (not issued)`. Payments start as Not Issued, and
  become Paid after payment goes through. Currently the other statuses
  can't be reached via code (failures in payment spew the error to the
  user) but can be set manually if appropriate.
- status: One of `PR (in progress), SB (submitted), FN (finalised), CX
  (cancelled)`. Bookings start in progress, move to submitted once a
  user has set a MIA, and optionally guests. A booking is set as
  finalised once payment has been processed and cancelled if a user
  cancels it or it is expired.
- reminder sent: a flag used by a management command which sends
  emails reminding users to fill out guests 2 weeks before stay.
- send admin email: A flag set via the admin form which, if set,
  causes a post save signal to send an email to the user similar to
  one they would receive if making a booking normally. It then gets unset.

Booking records can be browsed via the 'Bookings' entry in the admin
sidebar, or via the snippets menu. The display presents a summary of
current records and several filters. Booking records can be inspected
in depth via the '...' next to their name. Additionally the current
filtered selection can be exported to a spreadsheet via the '...' menu
at the top of the page.

## Booking System Flow

When a user searches a date range it is validated against the weekly
release of dates and for logical consistency. This range is then used
to generate a list of `BookingCartPeriod`s by consuming the time in
chunks according to the rules set by the season (or the date being
inside the last minute period) such that each chunk represents the
best attempt at a whole week. The `BookingCartPeriod`s are then tested
a to determine what rooms are impossible to book during that period
(because there are no legal bookings that would allow that room) and
this is used to generate a selection of rooms that can be booked for
the entire date range.

Once a user selects the rooms their selection is tested against the
season rules to ensure that adding this booking to their existing ones
will not exceed an allowed number of room-weeks. If it is a
`BookingRecord` is created and marked as in progress. As a
`BookingRecord` now exists the selected rooms will be marked as occupied.

Bookings which are 'in progress' and do not progress further are set
to 'cancelled' after 30 minutes from their last updated time.

After submission a user is sent to the edit page, where they must
nominate a member in attendance and optionally may fill in
guests. Here the `BookingCartPeriod`s are used to generate a summary
of the costs by counting the fee for the highest priority
`BookingType` in the period, subject to any weekly rate caps, and the
total is displayed. Once a user accepts the total and has set a MIA
the booking moves to the 'submitted' status and the room hold is
extended for 24 hours.

The user is directed to review the booking and pay. After payment is
received the booking is moved to the 'finalised' status and payment is
recorded along with a transaction ID, additionally a summary email is
sent to the member and the member in attendance. Prior to payment a
user may cancel a booking at any time via the '/my-bookings/'
page. After payment cancellation and refunds must be done manually.

A user can edit their attendees (but not the member in attendance) at
any time. A reminder email is sent asking members to confirm the
attendees one week out from the start date.

Users are shown a summary of all their upcoming bookings on their
'my-bookings' page.

### Important Note

It is hard-coded that 'Booking Page User Summary' must be at the url
'/my-bookings/' (configured via the slug) and 'Booking Page' must be
at '/make-a-booking/'.

## Ongoing Management of Booking Records

In general a booking should not be deleted. If a booking is refunded
or otherwise cancelled its status should be set to 'cancelled' and the
'payment status' updated accordingly. For this reason the
administration account, which has the ability to delete any item,
should not be used for proceedural management of bookings.

If a booking is created or edited via the administration interface a
Member will not normally be notified of the booking or changes
(although it will still display under their my-bookings summary). If a
user _should_ be notified then the administrator should tick the 'send
admin email' option on the form. If this is set a post-save signal
sends an email and then unsets it.

# Administration Commands

## Session clearing
A cron job setup to run the `clearsessions` command daily or so must be
configured to clear stale DB sessions

## Expired booking clearing
Bookings which are not finalised are expired via the expire-bookings
management command. A custom Manager is used to exclude these from
querysets so it is not critical that this is run frequently but in
order to maintain a clean administration UI it is recommended to run
`expire-bookings` at least daily.

## Sending reminder emails
A BookingRecord has a field `reminder_sent` this is used to mark
whether or not a reminder email has been sent. Emails reminding users
to fill out the guest list are sent 1 week out from the start date, or
at the earliest opportunity. Recommended to run `send-reminders` daily
early in the morning.

# User system

## Authentication

django-two-factor-auth is used. A post save/edit signal reinitialises
a default email otp device whenever an account is created or the email
updated. These otp devices can only be managed via the django admin
which is visited at /django-admin/.

The name being set to 'default' means it is required for login.

Management of OTP devices is done through django-admin, not
wagtail. If that ever needs to happen.

Booking system uses is_verified to ensure users logged in via 2fa to
make a booking. Accessing the booking pages checks when someone last
logged in, and if it's more than 1 day ago takes them to the login
page. The messages framework is used for explaining why.

django auth is used for handling logout and password resets. Using the
views under /account/, other than login which is handled by
two\_factor. Templates are under registration/ and two\_factor/.

# Setting up the website

## Deployment

- Download the relevant release
- Symlink the folder to /opt/wagtail/corroboree
- Set up a venv at /opt/wagtail/.venv and install requirements
- Configure settings/my.cnf for production database
- Set up a .env file with production configuration, must include:
  ```
  DJANGO_SETTINGS_MODULE=corroboree.settings.production
  PAYPAL_CLIENT_ID=
  PAYPAL_CLIENT_SECRET=
  PAYPAL_MERCHANT_EMAIL=
  SECRET_KEY=
  EMAIL_HOST=
  EMAIL_PORT=
  EMAIL_HOST_USER=
  EMAIL_HOST_PASSWORD=
  EMAIL_USE_SSL=True
  DEFAULT_FROM_EMAIL=
  BOOKING_FROM_EMAIL=
  OTP_EMAIL_SENDER=
  ```
- Make a folder /opt/wagtail/run and symlink deploy/gunicorn_start to
  /opt/wagtail/
- Link the gunicorn.service in deploy/ and enable and start it.
- run `python manage.py collectstatic --noinput`
- symlink nginx config to conf.d, editing the cert path and key path
- Make sure allowed hosts is set appropriately in settings, make sure
  the paypal environment is set appropriately.
- Set up the site content as described in
  [Configuration](#configuration) and [Pages](#pages).
- Redirect `/` to `/news`
- Ensure outbound email is possible in firewall rules.
- Add export of
  `DJANGO_SETTINGS_MODULE=corroboree.settings.production` to bashrc to
  avoid cascading fuck ups.
- Set up the crontab.

### Crontab

Set up the crontab to run the commands outlined in [Administration
Commands](#administration-commands) section.

An example config is below:

```
0 0 * * * export DJANGO_SETTINGS_MODULE=corroboree.settings.production && /opt/wagtail/.venv/bin/python /opt/wagtail/corroboree/manage.py clearsessions
0 0 * * * export DJANGO_SETTINGS_MODULE=corroboree.settings.production && /opt/wagtail/.venv/bin/python /opt/wagtail/corroboree/manage.py send-reminders
0 * * * * export DJANGO_SETTINGS_MODULE=corroboree.settings.production && /opt/wagtail/.venv/bin/python /opt/wagtail/corroboree/manage.py expire-bookings
```

## Configuration

(most) Administration is done via the `[site]/admin/` url which is the
wagtail administration interface. Configuration described in [Booking
System Configuration](#booking-system-configuration) takes effect
immediately upon saving. Navigating to 'Snippets' on the sidebar will
allow you to create the relevant objects (+ sign near name after
clicking) or edit existing ones. Some allow you to add additional
child snippets in their form (e.g. config lets you 'add
members'). Using this is fine, however as of 2024-11-30 some
validation safeguards are broken so bear that in mind.

### Things to ensure

- Every month in the calendar year is covered by a season.
- A `Member` with share number 0 exists for maintenance bookings.
- There is one `BookingType` for every sort of booking in *each*
  season they are active. If configuring a peak `Season` you will need
  to replicate the daily/weekly etc rates for that `Season` in the
  peak.
- If there should be a fee cap on daily bookings made in a week then
  one weekly booking in that season should be nominated to set that cap.
- `BookingType` priorities are set correctly (lower number means
  higher priority)/

## Pages

The following top level (i.e. under home) pages need to be set up:

- News (News page)
- About (Text page)
- Governance (Policies page)
- Rates (Rates page)
- Lodge Facilities and Features Guide (Text page)
- Contact Us (Contact page)
- Calendar (Booking calendar)
- Make a Booking (Booking page)
- My Booking (Booking page user summary)

Filling out relevant section should mostly be self explanetary
Governance, Contact, and Rates may need more explanation. If
doubt remains the 'publish' button in the right menu can be used to
preview. A page must be 'Published' to be live. In the 'Promote' tab
the 'Slug' sets the sub url. Additionally all of these top-level pages
should have 'Show in menus' ticked. Order in the navigation menu can
be changed by using 'Sort menu order' in the '...' menu next to Home.

To add posts to the news page just add child pages.

### Important Considerations

* Any page which should be private. At minimum:

  - Make a Booking
  - My Bookings
  - Contact Us

But I recommend all, should have the page set to private in the 'i'
menu in the information menu when creating or editing the page.

* The 'Slug' for Make a booking and My bookings must be set to:
  - make-a-booking
  - my-bookings

Respectively. These urls are used in other bits of code which can't
easily communicate with wagtail.

### Governance, Contact, and Rates

These pages use a wagtail structure called 'stream fields' which
enforces more structure on the contents of the page. Content is added
by way of adding 'blocks' that are packages of content which will be
displayed in a predefined way.

Governance uses the following:
- Policy, which refers to a child page of type 'Policy page' (this
  must be set up before adding a Policy)
- Section, which adds a subheading and optionally a paragraph of text
  introducing the section
- Policy with subpolicies, like Policy however you can also add child
  pages of the Policy page as indented links. Like Policy these must
  be saved before they can be added.
  
Rates uses the following:
- Season rates, a set of tables (add with +) that use a `Season` as a
  heading and below that have:
  - Rates, which is a display name and a `BookingType`. Note you are
    not restricted to bookings under the same season. This is so if a
    peak `Season` has the same rates you can display it under the same heading.
- Notes, a heading and then a series of notes under that heading

Contact Us uses the following:
- Heading, a heading
- Board contacts, a table of contacts with a position on the board
- Responsibility, a section which describes a responsibility and a
  member with that responsibility

## Users

### User Groups

By default there are 2 groups that administration users can be
assigned to. Editors and Moderators.

Editor is a suitable role for anyone who is able to edit but not
publish changes to pages.

Additionally an administrator role should be created, along with a
booking officer role. Assigning permissions as appropriated. The
booking officer should only be able to edit and view booking
records.

Groups which should have access to the administration interface will
need that ticked.

Another group should be created called 'Members', give it no
permissions. It is used to make sure share accounts are separate from
administration accounts.

### Provisioning Users

As of 2024-12-06 provisioning and onboarding new users is a somewhat
manual process. See
https://github.com/NaevaTheCat/corroboree/issues/34 for updates.

For each share a user account should be set up. That user account
should be associated with a member during creation. The User should be
assigned the Member group. A password will need to be set for the user
(a site such as https://memorablepasswordgenerator.com/ can make the
process simpler). Once a user is created, email the user and tell them
to use the 'lost password' function of the website to change their
password. Alternatively you could email the user with their generated
password, but there is a risk they will not change it.

When a user account is created, a 2fa device is automatically created
using their email. These can be viewed at the `/django-admin/`
interface (same sign in) under 'OTP_EMAIL' email devices.

Every user must have an email device configured, named 'default'
although unless something breaks this shouldn't need touching.
