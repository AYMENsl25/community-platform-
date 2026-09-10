# Recover an account

1. Verify the requester through the normal email recovery flow; support never asks for passwords, session cookies, MFA secrets, or recovery codes.
2. Before the 30-day anonymization deadline, the member signs in through a newly issued session and cancels the pending deletion with CSRF protection.
3. After anonymization, direct identity is intentionally unrecoverable. Explain retained legally/operationally required audit and registration records without exposing other people’s data.
4. For a compromised account, revoke all session families, reset credentials, rotate/re-enroll MFA, review safe audit events, and notify the member through a verified channel.

Support cannot edit database identity fields or bypass the recovery deadline.
