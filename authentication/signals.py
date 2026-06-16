from django.dispatch import Signal

# Sent after a successful Google login that created/returned a user
# receivers should accept: sender, request, user
google_login_completed = Signal()
