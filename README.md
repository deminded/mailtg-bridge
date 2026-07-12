# mailtg-bridge

Provider-neutral, self-hostable bridge between a **Telegram user account** (via Telethon/MTProto) and an **email mailbox** — so you stay reachable through email when your Telegram is whitelist-restricted or you're away from it.

- **Inbound (Telegram → email):** your DMs (all) and channel/group updates (by whitelist or direct mention, configurable) are delivered to your mailbox — batched per dialog per polling cycle.
- **Outbound (email → Telegram):** reply to a delivered email and it is posted back to the original chat **as you** (user-client, not a bot).
- Polling-based, configurable periodicity; attachments by size; enable/disable by email command.

## Install and configure

Python 3.11 or newer is required. Create a virtual environment, run
`pip install -e .`, copy `.env.example` outside the checkout, fill it in, and
set the file to mode 0600. State, lock, temporary and Telethon session paths
must be absolute and outside the repository. Their directories are private
(0700); state/session/lock files are 0600.

Only implicit TLS (`ssl`) and explicit TLS upgrade (`starttls`) are accepted.
Plaintext IMAP or SMTP cannot be configured. Values in `WHITELIST_JSON` and
`MENTION_LIST_JSON` are Telegram usernames, numeric peer IDs, or `peer:topic`.
The default `BOOTSTRAP_MODE=tail` records the currently visible tail without
sending history; use `history` to deliver the available fetch window.

```sh
python -m mailtg_bridge --env /etc/mailtg-bridge/mailtg-bridge.env check-config
python -m mailtg_bridge --env /etc/mailtg-bridge/mailtg-bridge.env setup
python -m mailtg_bridge --env /etc/mailtg-bridge/mailtg-bridge.env run
```

`once --kind inbound|mailbox|all` is intended for diagnostics. `purge` applies
age and count retention immediately. Every mutating command takes the same
nonblocking lifetime flock; an overlapping instance exits with code 73.

Email control is a reply to a bridge-generated email and is exactly one line:
`MAILTG ON [token]` or `MAILTG OFF [token]`. Trust requires the configured user
address, explicit delivery to the bridge address, a retained bridge Message-ID,
and the configured token when nonempty. The state change and consume marker are
atomic; its confirmation is persisted and retried separately.

## Runtime semantics

Telegram messages are processed chronologically in one logical batch per
dialog and cycle. SMTP parts are measured after final MIME serialization.
Oversized attachments are represented by placeholders and batches split only
between messages. Ledger rows and the high-watermark cursor commit together
after every part succeeds, providing at-least-once delivery.

Email replies are posted before their consume marker is committed. A crash
between Telegram post and SQLite commit can therefore duplicate a post; this is
the accepted v1 at-least-once boundary because Telegram offers no idempotency
key. An ambiguous SMTP outcome can likewise duplicate mail. No accepted message
is skipped to avoid those duplicates.

The supplied systemd unit uses one long-running process, a dedicated user,
0077 umask and restricted writable paths. Install it from `deploy/` after
adjusting the virtualenv path.

## Security
The Telethon session grants full account access. Never commit it or the env
file. Secrets, tokens, sessions and message bodies are excluded from structured
logs; dialog identifiers are suitable for hashing before logging. Retention
means replies to mail older than the retained ledger window are intentionally
ignored as untrusted.

Run tests with `python3 -m pytest -q`. Network smoke authorization/posting is
manual and requires a dedicated test account; automated tests use fake ports.
