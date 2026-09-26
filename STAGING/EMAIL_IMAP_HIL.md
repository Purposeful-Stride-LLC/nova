# Email IMAP plugin - HIL notes
Installed: openclaw plugin id imap (@antarien/openclaw-channel-imap@0.1.0-alpha.7) with --accept-capabilities.
Status: installed+enabled; mailbox credentials NOT configured (deliberate).
Gateway restart may be needed for full load.

## Operator next
1. Dedicated mailbox only (not personal primary).
2. Configure IMAP/SMTP via openclaw config for plugin imap (prefer app password).
3. Keep allowlist + rate limits on.
4. NOVA send path: draft first; never send without HIL approve (mirror nova.msg.send).
5. Restart gateway after config.

## Never
- Auto-reply all mail
- Give mail agent broad tools + full palace memory
