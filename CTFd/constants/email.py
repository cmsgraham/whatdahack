DEFAULT_VERIFICATION_EMAIL_SUBJECT = "Confirm your account for {ctf_name}"
DEFAULT_VERIFICATION_EMAIL_BODY = (
    "Welcome to {ctf_name}!\n\n"
    "Your email confirmation code is:\n\n"
    "    {code}\n\n"
    "Enter this code on the confirmation page to activate your account.\n"
    "This code expires in 30 minutes."
)
DEFAULT_SUCCESSFUL_REGISTRATION_EMAIL_SUBJECT = "Successfully registered for {ctf_name}"
DEFAULT_SUCCESSFUL_REGISTRATION_EMAIL_BODY = (
    "You've successfully registered for {ctf_name}!"
)
DEFAULT_USER_CREATION_EMAIL_SUBJECT = "Message from {ctf_name}"
DEFAULT_USER_CREATION_EMAIL_BODY = (
    "A new account has been created for you for {ctf_name}.\n\n"
    "Username: {name}\n"
    "Password: {password}"
)
DEFAULT_PASSWORD_RESET_SUBJECT = "Password Reset Request from {ctf_name}"
DEFAULT_PASSWORD_RESET_BODY = (
    "Did you initiate a password reset on {ctf_name}? "
    "If you didn't initiate this request you can ignore this email.\n\n"
    "Your password reset code is:\n\n"
    "    {code}\n\n"
    "Enter this code on the password reset page to set a new password.\n"
    "This code expires in 30 minutes."
)
DEFAULT_PASSWORD_CHANGE_ALERT_SUBJECT = "Password Change Confirmation for {ctf_name}"
DEFAULT_PASSWORD_CHANGE_ALERT_BODY = (
    "Your password for {ctf_name} has been changed.\n\n"
    "If you did not request this change, please contact an administrator immediately."
)
