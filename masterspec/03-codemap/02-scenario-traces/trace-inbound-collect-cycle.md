---
type: scenario-trace
slug: trace-inbound-collect-cycle
factory: mailtg-bridge
status: draft
updated: 2026-07-13
generated: true
---
<!-- impl-tact (fix/oe-3.0-defects): DEFECT-3 (Telegram entities bold/italic/code/pre/text_link now
     rendered) and DEFECT-4 (Subject tag dm:/ch:/gr: per dict-source-type.md) fixed in mail_out.py.
     DEFECT-5 (MediaUnavailable crashing the whole tact) fixed for the download-time failure mode in
     orchestrator.py+mail_out.py; embed-time read failure and the oversize omit-vs-split ordering bug
     remain open (out of this impl-tact's 5 defect groups) — see the fn-media-in-email rows below. -->
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
| MIME превышает limit | `src/mailtg_bridge/mail_out.py` | 89 | Batch делится; single-message media затем заменяются markers. |
| Media download недоступно (`MediaUnavailable`) | `src/mailtg_bridge/orchestrator.py` | 57 | Per-message `try/except` → `DownloadedMedia(available=False)` marker вместо потери всего batch (DEFECT-5, fixed). |

## Обработка ошибок

| Ошибка (из сценария) | Файл | Строка | Механизм |
|---|---|---|---|
| Session invalid при list/fetch/media | `src/mailtg_bridge/orchestrator.py` | 34, 71 | `invalidate_session()`, немедленный выход из такта. |
| FloodWait/temporary Telegram/SMTP | `src/mailtg_bridge/orchestrator.py` | 35, 73 | Персистентный scoped exponential backoff; cursor не коммитится. |
| Peer unavailable | `src/mailtg_bridge/orchestrator.py` | 72 | Warning и продолжение со следующим диалогом. |
| Cleanup временного файла не удался | `src/mailtg_bridge/orchestrator.py` | 69 | Best-effort unlink; `OSError` поглощается. |

## Маппинг контракта живой эксплуатации

| Грань требования | Владелец в спецификации | Code Unit / конфигурация | Автотест | Live/e2e evidence или остаточный риск | Статус |
|---|---|---|---|---|---|
| -> fn-dm-batch-to-email/OE-LOAD | -> lp-dm-batch-to-email | `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle`; `src/mailtg_bridge/config.py:Settings.from_env` | `tests/integration/test_flows.py:test_polling_is_sublinear_in_dialog_count` | Interval/fetch limit конфигурируются; `top_id` gate делает fetch round-trips O(active). | implemented |
| -> fn-dm-batch-to-email/OE-INPUT | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway._message`; `src/mailtg_bridge/mail_out.py:render_entities` | `tests/unit/test_mail_out.py:test_body_shows_author_and_deeplink`; `tests/unit/test_mail_out.py:test_entities_render_as_html_markup` | Unicode/author/media-only и Telegram entities (bold/italic/code/pre/text-link) теперь рендерятся (fixed, DEFECT-3); reply quote и forwarded metadata по-прежнему не рендерятся (адаптер не заполняет `TgMessage.reply_quote`, нет поля forward) — открытый остаток, вне 5 групп этого impl-такта. | not-implemented |
| -> fn-dm-batch-to-email/OE-EVIDENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer._message`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery`; `src/mailtg_bridge/mail_out.py:SmtpMailer._archive_sent` | `tests/unit/test_state.py:test_cursor_monotonic_and_atomic_delivery`; `tests/unit/test_mail_out.py:test_sent_copy_archives_when_enabled`; `tests/unit/test_mail_out.py:test_subject_shows_dm_and_channel_tags` | Ledger и Sent mirror есть; Subject теперь строится как `dm:<отправитель>` по -> dict-source-type (fixed, DEFECT-4). | implemented |
| -> fn-dm-batch-to-email/OE-SOURCES | -> scn-inbound-collect-cycle | `src/mailtg_bridge/algorithms.py:is_addressed`; `src/mailtg_bridge/algorithms.py:_bot_allowed` | `tests/unit/test_algorithms.py:test_bot_policy_gates_dm` | Bot policy выполняется до DM always-pass. | implemented |
| -> fn-dm-batch-to-email/OE-SECURITY | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway.connect`; `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/logging.py:JsonFormatter` | `tests/unit/test_runtime.py:test_log_redaction_and_json`; `tests/unit/test_config.py:test_plaintext_and_relative_or_bad_limits_rejected` | Telegram session, фиксированный U и TLS-only mail transport; message bodies не логируются. | implemented |
| -> fn-dm-batch-to-email/OE-RESILIENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/orchestrator.py:BridgeService.record_failure`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery`; `src/mailtg_bridge/locking.py:LifetimeLock.acquire` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_state.py:test_cursor_monotonic_and_atomic_delivery`; `tests/unit/test_runtime.py:test_lock_exclusive_and_private` | Scoped backoff, atomic ledger+cursor, WAL/FULL SQLite и singleton lock реализованы. | implemented |
| -> fn-dm-batch-to-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/integration/test_flows.py:test_inbound_gate_delivery_cursor_and_echo`; `tests/unit/test_mail_out.py:test_oversize_splits_between_messages` | Cursor commit следует за всеми SMTP ack; transient failure оставляет batch для повтора; MIME limit обрабатывается до send. | implemented |
| -> fn-channel-update-to-email/OE-LOAD | -> lp-channel-update-to-email | `src/mailtg_bridge/telegram.py:TelethonGateway.list_tracked_dialogs`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/integration/test_flows.py:test_polling_is_sublinear_in_dialog_count` | Configured/all-dialog discovery, active top-id gate, interval и per-dialog limit реализованы. | implemented |
| -> fn-channel-update-to-email/OE-INPUT | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway._dialog`; `src/mailtg_bridge/algorithms.py:build_deeplink`; `src/mailtg_bridge/mail_out.py:render_entities` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_mail_out.py:test_entities_render_as_html_markup` | Public/private/topic routing и message entities (bold/italic/code/pre/text-link) реализованы (fixed, DEFECT-3); reply/forward форм по-прежнему не доведены до MIME — открытый остаток, вне 5 групп этого impl-такта. | not-implemented |
| -> fn-channel-update-to-email/OE-EVIDENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer._message`; `src/mailtg_bridge/algorithms.py:build_deeplink`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery` | `tests/unit/test_mail_out.py:test_subject_shows_sender_name_not_numeric_id`; `tests/unit/test_mail_out.py:test_subject_shows_dm_and_channel_tags` | Subject теперь строится как `ch:<название>` по -> dict-source-type (tightened, DEFECT-4), link указывает на message/topic, ledger+cursor фиксируют успех. | implemented |
| -> fn-channel-update-to-email/OE-SOURCES | -> scn-inbound-collect-cycle | `src/mailtg_bridge/algorithms.py:is_addressed`; `src/mailtg_bridge/algorithms.py:_bot_allowed` | `tests/unit/test_algorithms.py:test_addressing_all_modes`; `tests/unit/test_algorithms.py:test_bot_policy_gates_dm` | Bot deny предшествует whitelist/mention, неизвестный источник не проходит. | implemented |
| -> fn-channel-update-to-email/OE-SECURITY | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/logging.py:JsonFormatter` | `tests/unit/test_runtime.py:test_log_redaction_and_json`; `tests/unit/test_config.py:test_plaintext_and_relative_or_bad_limits_rejected` | Fixed recipient, TLS-only transport, generic/redacted logs. | implemented |
| -> fn-channel-update-to-email/OE-RESILIENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle`; `src/mailtg_bridge/orchestrator.py:BridgeService.record_failure`; `src/mailtg_bridge/locking.py:LifetimeLock.acquire` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_runtime.py:test_lock_exclusive_and_private` | Peer/temporary failure scoped to dialog, other dialogs continue, singleton enforced. | implemented |
| -> fn-channel-update-to-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/state.py:SQLiteStore.commit_delivery`; `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch` | `tests/integration/test_flows.py:test_inbound_gate_delivery_cursor_and_echo`; `tests/unit/test_mail_out.py:test_oversize_splits_between_messages` | SMTP ack boundary, no cursor advance on failure, oversize degradation/split present. | implemented |
| -> fn-media-in-email/OE-LOAD | -> lp-media-in-email | `src/mailtg_bridge/config.py:Settings`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_config.py:test_settings_defaults`; `tests/unit/test_mail_out.py:test_mime_plain_html_and_exact_limit` | Threshold/limit конфигурируются; media обрабатываются внутри выбранного batch. | implemented |
| -> fn-media-in-email/OE-INPUT | -> scn-inbound-collect-cycle | `src/mailtg_bridge/telegram.py:TelethonGateway.download_media`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_mail_out.py:test_inline_image_has_referenced_cid` | Download идёт в temp dir; все зарегистрированные downloaded paths удаляются в `finally`. | implemented |
| -> fn-media-in-email/OE-EVIDENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle`; `src/mailtg_bridge/mail_out.py:EmailComposer._render` | `tests/unit/test_mail_out.py:test_inline_image_has_referenced_cid`; `tests/integration/test_flows.py:test_media_unavailable_download_still_delivers_with_marker` | Успешные inline/file/omitted варианты есть; download failure (`MediaUnavailable`) теперь превращается в явный «media unavailable» marker, письмо всё равно доставлено (fixed, DEFECT-5). | implemented |
| -> fn-media-in-email/OE-SECURITY | -> scn-inbound-collect-cycle | `src/mailtg_bridge/__main__.py:load`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | — | Temp dir chmod 0700, файлы удаляются, содержимое media не логируется; unlink остаётся best-effort residual risk. | implemented |
| -> fn-media-in-email/OE-RESILIENCE | -> scn-inbound-collect-cycle | `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_mail_out.py:test_oversize_splits_between_messages`; `tests/integration/test_flows.py:test_media_unavailable_download_still_delivers_with_marker` | Oversize split/marker есть; download failure теперь деградирует к marker без срыва письма (fixed, DEFECT-5). Остаётся открытым (вне 5 групп этого impl-такта): порядок деградации всё ещё split-before-omit, а не обещанный omit-before-split; сбой `read_bytes()` на уже скачанном файле (embed-time) не обёрнут в fallback. | not-implemented |
| -> fn-media-in-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:EmailComposer.compose_batch`; `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_inbound_cycle` | `tests/unit/test_mail_out.py:test_oversize_splits_between_messages`; `tests/integration/test_flows.py:test_media_unavailable_download_still_delivers_with_marker` | Oversize path доставляем; `MediaUnavailable` на download больше не срывает письмо целиком (fixed, DEFECT-5). Остаточный риск (не в скоупе этого impl-такта): embed-time `read_bytes()` failure на уже скачанном файле по-прежнему не изолирован от доставки. | not-implemented |

## Висячие пятна

| Тип | Грань | Что отсутствует |
|---|---|---|
| missing | -> fn-dm-batch-to-email/OE-INPUT | Entities теперь рендерятся (fixed, DEFECT-3); reply_quote/forward metadata адаптер по-прежнему не заполняет (`TgMessage.reply_quote` остаётся `None`, forward-поля нет в domain-модели) — открытый остаток, вне 5 групп этого impl-такта. |
| missing | -> fn-channel-update-to-email/OE-INPUT | Симметрично DM path: entities фикс закрыт, reply-quote/forwarded presentation остаётся открытым остатком. |
| contract-gap | -> fn-media-in-email/OE-RESILIENCE | Download-failure→marker закрыт (fixed, DEFECT-5). Остаётся: oversize деградация всё ещё split-before-omit (обещан omit-before-split); нет try/fallback вокруг `read_bytes()` при embed уже скачанного файла. |
| missing | -> fn-media-in-email/OE-DELIVERY | `MediaUnavailable` больше не срывает доставку (fixed, DEFECT-5). Остаточный риск: embed-time `read_bytes()` failure на уже скачанном файле не изолирован от доставки текстовой части batch. |

## Связи
- Сценарий: -> scn-inbound-collect-cycle
- Алгоритмы: -> alg-addressing-gate, -> alg-batch-per-dialog-cycle, -> alg-oversize-degrade, -> alg-dedup-idempotency, -> alg-backoff-on-floodwait
- Компоненты: -> cmp-bridge-orchestrator, -> cmp-tg-gateway, -> cmp-email-out, -> cmp-state-store

