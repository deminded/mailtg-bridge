---
type: scenario-trace
slug: trace-inbound-collect-cycle
factory: mailtg-bridge
status: draft
updated: 2026-07-13
generated: true
---
# Code Trace: такт сбора Telegram → email

## Сценарий
- **Спецификация:** -> scn-inbound-collect-cycle
- **Триггер в коде:** `src/mailtg_bridge/orchestrator.py:BridgeService.run` — наступил `collect_interval_seconds`.

## Цепочка вызовов

| # | Шаг сценария | Компонент | Code Unit | Kind | Файл | Описание |
|---|---|---|---|---|---|---|
| 1 | 1 | -> cmp-bridge-orchestrator | `BridgeService.delivery_allowed()` | call | `src/mailtg_bridge/orchestrator.py:BridgeService.delivery_allowed` | Гейт bridge enabled + session valid. |
| 2 | 2 | -> cmp-state-store | `SQLiteStore.get_cursor()` | db-query | `src/mailtg_bridge/state.py:SQLiteStore.get_cursor` | Читает/создаёт курсор диалога. |
| 3 | 3 | -> cmp-tg-gateway | `list_tracked_dialogs()` / `fetch_since()` | external-call | `src/mailtg_bridge/telegram.py:TelethonGateway.list_tracked_dialogs`; `src/mailtg_bridge/telegram.py:TelethonGateway.fetch_since` | Обнаруживает диалоги и выбирает сообщения после cursor. |
| 4 | 4–5 | -> cmp-tg-gateway | `SQLiteStore.is_echo()` / `is_addressed()` | cache-read/call | `src/mailtg_bridge/state.py:SQLiteStore.is_echo`; `src/mailtg_bridge/algorithms.py:is_addressed` | Удаляет own echo, затем применяет bot/source/mention gate. |
| 5 | 6 | -> cmp-bridge-orchestrator | `make_dialog_batch()` | call | `src/mailtg_bridge/algorithms.py:make_dialog_batch` | Сортирует прошедшие сообщения по msg id. |
| 6 | 7 | -> cmp-tg-gateway | `TelethonGateway.download_media()` | external-call | `src/mailtg_bridge/telegram.py:TelethonGateway.download_media` | Загружает media во временный каталог. |
| 7 | 8–10 | -> cmp-email-out | `EmailComposer.compose_batch()` | call | `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch` | Формирует MIME, inline/attachment/marker и режет oversized batch. |
| 8 | 11 | -> cmp-email-out | `SmtpMailer.send()` | external-call | `src/mailtg_bridge/mail_out.py:SmtpMailer.send` | Отправляет B→U по TLS SMTP и получает transport success. |
| 9 | 12 | -> cmp-state-store | `SQLiteStore.commit_delivery()` | db-query | `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery` | Атомарно пишет ledger и продвигает cursor после всех SMTP ack. |
| 10 | cleanup | -> cmp-bridge-orchestrator | `BridgeService.run_inbound_cycle()` finally | call | `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | Удаляет каждый скачанный временный файл. |

## Ветвления в коде

| Условие (из сценария) | Файл | Строка | Как реализовано |
|---|---|---|---|
| Bridge OFF/session invalid/backoff active | `src/mailtg_bridge/orchestrator.py` | 32 | Ранний `return`, Telegram polling не начинается. |
| Диалог неактивен (`top_id <= cursor`) | `src/mailtg_bridge/orchestrator.py` | 40 | Fetch не вызывается, что сохраняет O(active) invariant. |
| Первый tail-bootstrap | `src/mailtg_bridge/orchestrator.py` | 46 | Cursor ставится на high watermark без исторической доставки. |
| Own echo или неадресованное сообщение | `src/mailtg_bridge/orchestrator.py` | 48 | List comprehension исключает его до batch/media. |
| Ни одно сообщение не прошло gate | `src/mailtg_bridge/orchestrator.py` | 51 | Cursor продвигается, письмо не создаётся. |
| MIME превышает limit | `src/mailtg_bridge/mail_out.py` | 58 | Batch делится; single-message media затем заменяются markers. |

## Обработка ошибок

| Ошибка (из сценария) | Файл | Строка | Механизм |
|---|---|---|---|
| Session invalid при list/fetch/media | `src/mailtg_bridge/orchestrator.py` | 34, 65 | `invalidate_session()`, немедленный выход из такта. |
| FloodWait/temporary Telegram/SMTP | `src/mailtg_bridge/orchestrator.py` | 35, 67 | Персистентный scoped exponential backoff; cursor не коммитится. |
| Peer unavailable | `src/mailtg_bridge/orchestrator.py` | 66 | Warning и продолжение со следующим диалогом. |
| Cleanup временного файла не удался | `src/mailtg_bridge/orchestrator.py` | 63 | Best-effort unlink; `OSError` поглощается. |

## Маппинг контракта живой эксплуатации

| Грань требования | Владелец в спецификации | Code Unit / конфигурация | Автотест | Live/e2e evidence или остаточный риск | Статус |
|---|---|---|---|---|---|
| -> fn-dm-batch-to-email/OE-LOAD | -> lp-dm-batch-to-email | `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle`; `src/mailtg_bridge/config.py:Settings.from_env` | `tests/integration/test_flows.py:test_polling_is_sublinear_in_dialog_count` | Interval/fetch limit конфигурируются; `top_id` gate делает fetch round-trips O(active). | implemented |
| -> fn-dm-batch-to-email/OE-INPUT | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway._message`; `src/mailtg_bridge/mail_out.py:EmailComposer._render` | `tests/unit/test_mail_out.py:test_body_shows_author_and_deeplink` | Unicode/author/media-only есть, но Telegram entities, reply quote и forwarded metadata не рендерятся в письмо. | not-implemented |
| -> fn-dm-batch-to-email/OE-EVIDENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer._message`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery`; `src/mailtg_bridge/mail_out.py:SmtpMailer._archive_sent` | `tests/unit/test_state.py:test_cursor_monotonic_and_atomic_delivery`; `tests/unit/test_mail_out.py:test_sent_copy_archives_when_enabled` | Ledger и Sent mirror есть, но требуемый тег Subject `dm:<отправитель>` заменён на `Telegram: <name>`. | not-implemented |
| -> fn-dm-batch-to-email/OE-SOURCES | -> scn-inbound-collect-cycle | `src/mailtg_bridge/algorithms.py:is_addressed`; `src/mailtg_bridge/algorithms.py:_bot_allowed` | `tests/unit/test_algorithms.py:test_bot_policy_gates_dm` | Bot policy выполняется до DM always-pass. | implemented |
| -> fn-dm-batch-to-email/OE-SECURITY | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway.connect`; `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/logging.py:JsonFormatter` | `tests/unit/test_runtime.py:test_log_redaction_and_json`; `tests/unit/test_config.py:test_plaintext_and_relative_or_bad_limits_rejected` | Telegram session, фиксированный U и TLS-only mail transport; message bodies не логируются. | implemented |
| -> fn-dm-batch-to-email/OE-RESILIENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/orchestrator.py:BridgeService.record_failure`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery`; `src/mailtg_bridge/locking.py:LifetimeLock.acquire` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_state.py:test_cursor_monotonic_and_atomic_delivery`; `tests/unit/test_runtime.py:test_lock_exclusive_and_private` | Scoped backoff, atomic ledger+cursor, WAL/FULL SQLite и singleton lock реализованы. | implemented |
| -> fn-dm-batch-to-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/integration/test_flows.py:test_inbound_gate_delivery_cursor_and_echo`; `tests/unit/test_mail_out.py:test_oversize_splits_between_messages` | Cursor commit следует за всеми SMTP ack; transient failure оставляет batch для повтора; MIME limit обрабатывается до send. | implemented |
| -> fn-channel-update-to-email/OE-LOAD | -> lp-channel-update-to-email | `src/mailtg_bridge/telegram.py:TelethonGateway.list_tracked_dialogs`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/integration/test_flows.py:test_polling_is_sublinear_in_dialog_count` | Configured/all-dialog discovery, active top-id gate, interval и per-dialog limit реализованы. | implemented |
| -> fn-channel-update-to-email/OE-INPUT | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway._dialog`; `src/mailtg_bridge/algorithms.py:build_deeplink`; `src/mailtg_bridge/telegram.py:TelethonGateway._message` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_mail_out.py:test_body_shows_author_and_deeplink` | Public/private/topic routing реализован, но общий обещанный набор message entities/reply/forward форм не доведён до MIME. | not-implemented |
| -> fn-channel-update-to-email/OE-EVIDENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer._message`; `src/mailtg_bridge/algorithms.py:build_deeplink`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery` | `tests/unit/test_mail_out.py:test_subject_shows_sender_name_not_numeric_id`; `tests/unit/test_mail_out.py:test_body_shows_author_and_deeplink` | Subject идентифицирует источник, link указывает на message/topic, ledger+cursor фиксируют успех. | implemented |
| -> fn-channel-update-to-email/OE-SOURCES | -> scn-inbound-collect-cycle | `src/mailtg_bridge/algorithms.py:is_addressed`; `src/mailtg_bridge/algorithms.py:_bot_allowed` | `tests/unit/test_algorithms.py:test_addressing_all_modes`; `tests/unit/test_algorithms.py:test_bot_policy_gates_dm` | Bot deny предшествует whitelist/mention, неизвестный источник не проходит. | implemented |
| -> fn-channel-update-to-email/OE-SECURITY | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/logging.py:JsonFormatter` | `tests/unit/test_runtime.py:test_log_redaction_and_json`; `tests/unit/test_config.py:test_plaintext_and_relative_or_bad_limits_rejected` | Fixed recipient, TLS-only transport, generic/redacted logs. | implemented |
| -> fn-channel-update-to-email/OE-RESILIENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle`; `src/mailtg_bridge/orchestrator.py:BridgeService.record_failure`; `src/mailtg_bridge/locking.py:LifetimeLock.acquire` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_runtime.py:test_lock_exclusive_and_private` | Peer/temporary failure scoped to dialog, other dialogs continue, singleton enforced. | implemented |
| -> fn-channel-update-to-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery`; `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch` | `tests/integration/test_flows.py:test_inbound_gate_delivery_cursor_and_echo`; `tests/unit/test_mail_out.py:test_oversize_splits_between_messages` | SMTP ack boundary, no cursor advance on failure, oversize degradation/split present. | implemented |
| -> fn-media-in-email/OE-LOAD | -> lp-media-in-email | `src/mailtg_bridge/config.py:Settings`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_config.py:test_settings_defaults`; `tests/unit/test_mail_out.py:test_mime_plain_html_and_exact_limit` | Threshold/limit конфигурируются; media обрабатываются внутри выбранного batch. | implemented |
| -> fn-media-in-email/OE-INPUT | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway.download_media`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_mail_out.py:test_inline_image_has_referenced_cid` | Download идёт в temp dir; все зарегистрированные downloaded paths удаляются в `finally`. | implemented |
| -> fn-media-in-email/OE-EVIDENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer._render`; `src/mailtg_bridge/mail_out.py:EmailComposer._message` | `tests/unit/test_mail_out.py:test_inline_image_has_referenced_cid` | Успешные inline/file/omitted варианты есть; download failure не превращается в явный «media unavailable» marker. | not-implemented |
| -> fn-media-in-email/OE-SECURITY | -> scn-inbound-collect-cycle | `src/mailtg_bridge/__main__.py:load`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | — | Temp dir chmod 0700, файлы удаляются, содержимое media не логируется; unlink остаётся best-effort residual risk. | implemented |
| -> fn-media-in-email/OE-RESILIENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_mail_out.py:test_oversize_splits_between_messages` | Oversize split/marker есть, но download/embed failure не деградирует к marker; порядок также split-before-omit, а не обещанный omit-before-split. | not-implemented |
| -> fn-media-in-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch`; `src/mailtg_bridge/mail_out.py:SmtpMailer.send` | `tests/unit/test_mail_out.py:test_oversize_splits_between_messages` | Oversize path доставляем, но MediaUnavailable/read failure может сорвать письмо целиком вместо деградации. | not-implemented |

## Висячие пятна

| Тип | Грань | Что отсутствует |
|---|---|---|
| missing | -> fn-dm-batch-to-email/OE-INPUT | `_message()` сохраняет entities, но `_render()` их игнорирует; reply_quote/forward metadata адаптер не заполняет и composer не показывает. |
| contract-gap | -> fn-dm-batch-to-email/OE-EVIDENCE | Subject строится как `Telegram: <name>`, не как требуемый `dm:<sender>`. |
| missing | -> fn-channel-update-to-email/OE-INPUT | Форматирование entities, цитата-ответ и forwarded presentation отсутствуют так же, как в DM path. |
| missing | -> fn-media-in-email/OE-EVIDENCE | `download_media()` exception выходит во внешний handler; marker «вложение недоступно» не создаётся. |
| contract-gap | -> fn-media-in-email/OE-RESILIENCE | Нет try/fallback вокруг `read_bytes()`/inline embedding; oversize деградация выполняется в обратном заявленному порядке. |
| missing | -> fn-media-in-email/OE-DELIVERY | Media failure не изолирован от доставки текстовой части batch. |

## Связи
- Сценарий: -> scn-inbound-collect-cycle
- Алгоритмы: -> alg-addressing-gate, -> alg-batch-per-dialog-cycle, -> alg-oversize-degrade, -> alg-dedup-idempotency, -> alg-backoff-on-floodwait
- Компоненты: -> cmp-bridge-orchestrator, -> cmp-tg-gateway, -> cmp-email-out, -> cmp-state-store

