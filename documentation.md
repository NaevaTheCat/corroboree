# Config notes
Member 0 is dummy member for maintenance bookings

Currently validation is clean() methods for children of
`ClusterableModel`s is broken. You have a choice between a convenient
interface and being able to screw yourself over. Make whatever
decision you feel comfortable with.

# Booking System Notes

# Site layout and formatting
Menu order is adjusted by adjusting 'sort menu order' in the edit menu
of the homepage.

# Administration Commands

## Session clearing
A cron job setup to run the clearsessions command daily or so must be
configured to clear stale DB sessions

## Expired booking clearing
Bookings which are not finalised are expired via the expire-bookings
management command. A custom Manager is used to exclude these from
querysets so it is not critical that this is run frequently but in
order to maintain a clean administration UI it is recommended to run
this task at least once an hour via the crontab

## Sending reminder emails
A BookingRecord has a field `reminder_sent` this is used to mark
whether or not a reminder email has been sent. Emails reminding users
to fill out the guest list are sent 1 week out from the start date, or
at the earliest opportunity. Recommended to run daily.

# User system

## Authentication

django-two-factor-auth is used. A post save/edit signal reinitialises
a default email otp device whenever an account is created or the email
updated.

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

