# How Garmin credentials are handled

This app talks to Garmin Connect so it can import your activities. It does **not** keep your Garmin password.

## What you type

On **Settings**, Connect asks for your Garmin email and password (and an MFA code if Garmin requires one). Those values are used **once**, in memory, to log in to Garmin.

## What is stored

| Item | Stored? |
|------|---------|
| Garmin password | **No** |
| Garmin email | Yes, so the UI can show which account is connected |
| Garmin session | Yes — OAuth/refresh tokens from [garth](https://github.com/matin/garth), encrypted at rest with Fernet (`TOKEN_ENCRYPTION_KEY`) |
| App account password | bcrypt hash only (this is your tracker login, not Garmin) |

After a successful Connect, the password is discarded. **Sync now** decrypts the saved session and calls Garmin with that session. It never sends or reads your Garmin password.

If Garmin’s session expires, you Connect again. A normal incremental sync does not ask for the password.

## MFA

If Garmin challenges MFA, a short-lived pending-login blob is stored (DynamoDB TTL ~10 minutes) so the follow-up code can finish login. That item is deleted when MFA succeeds or you disconnect.

## What sync imports

Sync pulls **all** Garmin activities in the date range (365-day first backfill, then incremental). They are accepted automatically. The week grid still treats **run / hike / stair** as the distance and elevation totals; calories include every activity.
