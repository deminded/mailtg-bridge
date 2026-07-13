---
type: load-profile
slug: lp-bridge-control-by-email
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-13
---
# Профиль нагрузки: управление мостом письмом

## Основание
-> fn-bridge-control-by-email/OE-LOAD: команды — редкие ручные события (не поток), но обнаруживаются
тем же тактом опроса ящика B, что и ответы: период опроса `SEND_INTERVAL_SECONDS` (дефолт 30 с,
конфигурируем); команда обрабатывается в пределах одного такого интервала независимо от нагрузки на
другие функции. Источник: код `config.py` (`SEND_INTERVAL_SECONDS`), `orchestrator.py`
(`run_mailbox_cycle`).
