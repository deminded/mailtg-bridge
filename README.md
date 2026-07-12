# mailtg-bridge

Provider-neutral, self-hostable bridge between a **Telegram user account** (via Telethon/MTProto) and an **email mailbox** — so you stay reachable through email when your Telegram is whitelist-restricted or you're away from it.

- **Inbound (Telegram → email):** your DMs (all) and channel/group updates (by whitelist or direct mention, configurable) are delivered to your mailbox — batched per dialog per polling cycle.
- **Outbound (email → Telegram):** reply to a delivered email and it is posted back to the original chat **as you** (user-client, not a bot).
- Polling-based, configurable periodicity; attachments by size; enable/disable by email command.

## Status: requirements draft (WIP)
This repo currently holds the **requirements** for review, produced via the [masterspec](https://github.com/deminded/masterspec) SDD flow:

- `_input/tickets.md` — business-requirement tickets (TKT-TMB-1..8)
- `_input/arch-sketch.md` — architecture sketch
- `masterspec-config.yaml` — guardrail packs + severity policy

Next: `derive layer=req` → `verify` → hand to Codex for implementation. Reuses proven pieces (Telethon polling, IMAP/SMTP with threading, dedup ledger).

## Security
The Telethon session file grants full account access — keep it `chmod 600` and out of the repo. See TKT-TMB-7.
