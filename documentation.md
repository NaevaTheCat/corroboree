# Config notes
Member 0 is dummy member for maintenance bookings

# Booking System Notes

# Site layout and formatting
Menu order is adjusted by adjusting 'sort menu order' in the edit menu
of the homepage. 

# 2fa

django-two-factor-auth is used. A post save/edit signal reinitialises
a default email otp device whenever an account is created or the email
updated.

The name being set to 'default' means it is required for login.

Management of OTP devices is done through django-admin, not
wagtail. If that ever needs to happen.

Booking system uses is_verified to ensure users logged in via 2fa to
make a booking
