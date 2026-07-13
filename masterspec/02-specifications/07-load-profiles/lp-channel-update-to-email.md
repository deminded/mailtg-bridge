---
type: load-profile
slug: lp-channel-update-to-email
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-13
---
# Профиль нагрузки: доставка обновлений каналов и групп

## Основание
-> fn-channel-update-to-email/OE-LOAD: популяция — сконфигурированный набор отслеживаемых источников
(белый список ∪ список упоминаний), либо все диалоги аккаунта при `DISCOVER_ALL_DIALOGS=true` и
`MENTION_POLICY=all`; активное подмножество — источники с новыми сообщениями после курсора; частота
такта — `COLLECT_INTERVAL_SECONDS` (дефолт 60 с); выборка за такт ограничена `TG_FETCH_LIMIT` (дефолт
100/диалог); backlog после простоя пересобирается без потери. Ключи `DISCOVER_ALL_DIALOGS`,
`MENTION_POLICY`, `COLLECT_INTERVAL_SECONDS`, `TG_FETCH_LIMIT` — контракт -> data-config. Тот же
инвариант масштабирования, что и для личных сообщений (round-trips ≈ O(активные), не O(все)) —
использует общий цикл опроса, -> fn-dm-batch-to-email/OE-LOAD. Источник: код `config.py`
(`DISCOVER_ALL_DIALOGS`, `COLLECT_INTERVAL_SECONDS`, `TG_FETCH_LIMIT`), `telegram.py`
(`list_tracked_dialogs`).
