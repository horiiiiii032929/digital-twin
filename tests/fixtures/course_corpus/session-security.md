# Session security

An authenticated session lets a server associate later requests with a user.
Session identifiers should be unpredictable, protected in transit, and rotated
after authentication.

## Misconception

A session cookie is not the same thing as a password. Stealing either can be
harmful, but the mechanisms and mitigations differ.
