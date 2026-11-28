# Security notes

## What protects the app
| Area | Measure |
|---|---|
| Sign-in | scrypt password hashes; constant-time check even for unknown users; lock after 5 wrong tries per address and 12 per username (5 min); password change signs out the user's other sessions |
| Passwords | 10-128 chars, not the username, not a common/simple password |
| Sessions | HttpOnly, SameSite=Strict, `__Host-` cookie + Secure over https, 30 min idle timeout, new session id after login |
| CSRF | every POST needs the `X-CSRF-Token` header |
| Permissions | per user (Report, Import, Send, Expiry, Fill ID, Export, Admin) checked **on the server** for every API call; only the main admin (`ADMIN_USER`) can create/modify an Admin |
| Uploads | 10 MB limit, content checked (real .xlsx zip / real text CSV), zip-bomb guard, formula-injection neutralised on export |
| Browser | strict CSP (no inline script), nosniff, no framing, no referrer, COOP/CORP, Permissions-Policy, HSTS on https |
| Errors | tracebacks stay in the server log, never sent to the browser |
| Secrets | only in environment variables; `.env` is git-ignored and not copied into the Docker image |

## Must do (once)
1. **Rotate** every secret that was ever committed (an old `.env` was on GitHub): `SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `API_HASH`, `TELEGRAM_SESSION_STRING`, database password. Git history keeps old files.
2. Set `COOKIE_SECURE=1` and `TRUST_PROXY=1` on Render (the Dockerfile already does).
3. Give each person their own account with only the permissions they need.

## Known limits
- Login throttle is kept in memory (resets on restart, per process).
- The Docker container runs as root because Chromium (table image) needs `--no-sandbox` then; it only renders HTML built from escaped client data.
