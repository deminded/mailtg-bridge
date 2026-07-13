---
type: load-profile
slug: lp-dm-batch-to-email
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-13
---
# Профиль нагрузки: доставка личных сообщений батчем

## Основание
-> fn-dm-batch-to-email/OE-LOAD: популяция — все личные диалоги аккаунта (эмпирика живого теста: до
~806 на одном аккаунте, -> nfr-operability/NFR-OPS-LOAD); активное подмножество за такт — диалоги с
новыми сообщениями после курсора; частота такта — `COLLECT_INTERVAL_SECONDS` (дефолт 60 с,
конфигурируем); выборка за такт ограничена `TG_FETCH_LIMIT` (дефолт 100 сообщений/диалог); backlog
после простоя пересобирается с сохранённого курсора на последующих тактах без потери. Инвариант
масштабирования: число сетевых round-trip за такт ≈ O(активные диалоги), не O(все диалоги). Ключи
конфигурации `COLLECT_INTERVAL_SECONDS`, `TG_FETCH_LIMIT` — контракт -> data-config. Источник:
код `config.py` (`COLLECT_INTERVAL_SECONDS`, `TG_FETCH_LIMIT`), `orchestrator.py`
(`run_inbound_cycle`); -> nfr-operability.
