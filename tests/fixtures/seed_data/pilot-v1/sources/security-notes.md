# Demo Browser Security: session controls

## Sessions
After authentication, a session cookie can identify a server-side session. The server must check session validity and authorization on protected requests. Logout revokes the session in this course's example application.

## Cookie controls
Secure restricts transmission to secure connections. HttpOnly prevents JavaScript from reading the cookie through document.cookie; it does not prevent every action an injected script could perform. SameSite controls cookie inclusion in cross-site request contexts.

## CSRF
A browser can automatically attach cookies to requests. This is why cookie authentication alone is not a complete CSRF defense. In the course example, state-changing requests require a permitted Origin; token-based defenses are another approach outside this example's implementation scope.

## Contrast question
HttpOnly limits cookie access by script; it does not by itself prove that a state-changing request was intended by the user.
