# Codex design-gate brief — mailtg-bridge

Ты — РЕАЛИЗАТОР (gpt-5.6-sol). Сейчас ДИЗАЙН-ГЕЙТ: произвести имплементационный ДИЗАЙН по готовой спецификации. НЕ писать код на этом шаге — только дизайн-документ. Его ревьюит Арет перед тем, как ты начнёшь код.

## Что производишь
Файл `/home/claude-user/mailtg-bridge/DESIGN.md` — имплементационный план на Python:
1. Структура модулей/файлов проекта (src/, что где).
2. Маппинг спеки → код: каждый cmp-* → модуль/класс; каждый scn-* → поток; alg-* → функции; api-* → адаптеры; data-bridge-store → слой персистентности.
3. **Переиспользование обкатанного ядра** (НЕ писать с нуля): изучи и опирайся на:
   - `/home/claude-user/channel-reader/reader.py` — паттерн Telethon-поллинга каналов с per-channel курсором.
   - `/home/claude-user/email_poller.py` + `/home/claude-user/de-agent-commons/src/agentcommons/email.py` — IMAP/SMTP, тред, дедуп-ledger (`MessageLedger`), `is_allowed`, `is_auto_or_loop`, `send_email`.
   - `/home/claude-user/arete-userbot/` — Telethon user-session (auth, get_messages, send).
   Явно укажи, что берём из ядра, что пишем новое, где адаптируем.
4. Ключевые решения реализации: high-watermark курсор (толерантен к удалённым/gap id — см. alg-batch-per-dialog-cycle), flock single-instance, порядок commit send→ledger→cursor (at-least-once), session-health (валидна/невалидна→стоп+алерт), backoff на FloodWait, HTML-письмо с inline-картинками + deep-link, токен-команды.
5. Схема `.env` (все конфиг-поля из data-bridge-store: B-креды/host/port, U-адрес, whitelist, mention-policy, пороги, интервалы, токен, retention).
6. Форма деплоя (systemd-таймер или один процесс-loop + flock; docker опц.), интерактивный `setup` для Telethon-сессии.
7. Точки риска и открытые вопросы к Арету.

## Вход (читай ПРИЦЕЛЬНО, не топи контекст)
- Спека: `/home/claude-user/mailtg-bridge/masterspec/02-specifications/` — начни с `00-masterspec-index.md`, читай компоненты/сценарии/алгоритмы/api/data по ссылкам, а не всё подряд.
- Требования для контекста: `/home/claude-user/mailtg-bridge/masterspec/01-requirements/` (as, cdm-bridge, fn-*, rules-*, nfr-*).
- Verify-ответы (учтённые дефекты): `masterspec/verify-response-req.md`, `masterspec/verify-response-spec.md`.

## Дисциплина (урок Sol 12.07)
- Узкий мандат: ТОЛЬКО DESIGN.md, не код. Не пиши файлы кода на этом шаге.
- Чекпоинт: пиши DESIGN.md инкрементально по мере проработки, не держи всё в голове до конца.
- Не топи: читай спеку прицельно (по индексу и ссылкам), не поглощай весь masterspec-фреймворк.
- Язык кода — Python. Стиль — как в переиспользуемом ядре.

Итог твоего хода — краткое резюме: структура модулей, что переиспользуешь, 3-5 ключевых решений, открытые вопросы. Файл DESIGN.md — основной результат.
