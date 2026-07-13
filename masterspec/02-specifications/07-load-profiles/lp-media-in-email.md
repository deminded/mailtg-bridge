---
type: load-profile
slug: lp-media-in-email
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-13
---
# Профиль нагрузки: представление медиа и вложений в письме

## Основание
-> fn-media-in-email/OE-LOAD: популяция — вложения сообщений батча текущего такта (0..N на
сообщение); порог файл/указание — `ATTACHMENT_THRESHOLD_BYTES` (дефолт 10 МБ), лимит письма —
`EMAIL_SIZE_LIMIT_BYTES` (дефолт ~24 МБ), оба конфигурируемы (контракт обоих ключей -> data-config);
рост пропорционален числу медиа-сообщений батча диалога, не является отдельным от
-> fn-dm-batch-to-email/OE-LOAD / -> fn-channel-update-to-email/OE-LOAD тактом. Источник: код
`config.py` (`ATTACHMENT_THRESHOLD_BYTES`, `EMAIL_SIZE_LIMIT_BYTES`).
