# Race Operations v0.9.0: monitor mutes and SES email

Install on the CLOUD Windows PC only. Requires working backend v0.8.0 or v0.9.0. No DVR agent update needed.

Extract the ZIP, open Administrator PowerShell in that directory, then:

```powershell
Get-ChildItem -Recurse -File | Unblock-File
.\Update-Alerts.ps1
```

Only Race Operations Backend restarts. The updater backs up installed files and rolls them back if startup validation fails. It refuses pending recovery actions. Refresh the dashboard with Ctrl+F5 and sign in.

## SES setup

Choose one AWS SES region. Verify your sender email/domain there. If the account is still in the SES sandbox, verify the destination email there too. Create SES SMTP credentials for the same region; these are different from AWS access keys or your console login.

- https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html
- https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html

Run locally on the cloud PC (change region if needed):

```powershell
.\Configure-SES.ps1 -Region us-east-1
```

The wizard prompts for sender, recipient and SMTP credentials, sends ONE test email, then enables automatic alerts after SES accepts it. Check your inbox/spam folder. Credentials are stored in a file restricted to SYSTEM and Administrators; they are not exposed by the dashboard. SMTP uses STARTTLS on port 587. A failed test leaves sending disabled.

Disable all email delivery:

```powershell
.\Configure-SES.ps1 -Disable
```

## Behavior

- Each monitor has a persistent Mute alerts toggle, shared by dashboard sessions and retained after restarts.
- Muting suppresses email only. Status colors, health checks, and recovery controls remain active.
- Continuous red for 30 seconds queues one email. Green/yellow recovery allows a new email for the next red incident. Unknown is not recovery.
- An already-red monitor can alert when email is first enabled or it is unmuted, unless that incident was already sent.
- The Agent connection monitor goes red after a previously seen PC stops reporting for 45 seconds. Backend startup allows 60 seconds for reconnection, followed by the red delay.
- Individual stale service checks stay Unknown. The connector reflects the fresh cloud proxy's connection report.
- A muted monitor may still receive an email already handed to SMTP before the mute was saved.
- The notification log shows recent outcomes. Accepted means SES accepted the message, not guaranteed inbox delivery. Rejected/failed needs configuration or connectivity investigation. Uncertain means delivery may have occurred; it is deliberately not retried.
- Transient failures known to occur before acceptance are retried up to three attempts. Accepted incidents persist across backend restarts.
- No recovery emails or repeating reminders are sent.
- The cloud backend must be running and have network access to send. Total cloud-PC/backend failure needs an external watchdog; this update does not add one.

## Safe first check

Mute a noncritical monitor, let it go red, and verify its color still changes without an email. Unmute it while it stays red and allow the 30-second threshold. Verify one email and an accepted log entry, then recover it. Do not stop OBS during recording or restart judging services during a critical transaction.

## Validation

Python unit/API tests cover incident persistence, mute authorization, thresholds, SES transport and bounded retries. Chromium checks cover 1440, 768, 390 and 320 pixel widths, mute toggling, details persistence and recovery confirmation. Windows installation and real SES delivery must be verified on the cloud PC; no live credentials or email sends were used in development.
