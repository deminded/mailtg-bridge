---
type: scenario-trace
slug: trace-outbound-reply
factory: mailtg-bridge
status: draft
updated: 2026-07-13
generated: true
---
# Code Trace: ответ из email в Telegram

## Сценарий
- **Спецификация:** -> scn-outbound-reply
- **Триггер в коде:** `src/mailtg_bridge/orchestrator.py:BridgeService.run_mailbox_cycle` — получено непотреблённое письмо из IMAP.

## Цепочка вызовов

| # | Шаг сценария | Компонент | Code Unit | Kind | Файл | Описание |
|---|---|---|---|---|---|---|
| 1 | 1 | -> cmp-email-in | `ImapMailbox.poll()` | external-call | `src/mailtg_bridge/mail_in.py:ImapMailbox.poll` | Загружает MIME без установки `Seen`. |
| 2 | 2–4 | -> cmp-email-in | `parse_inbound()` / `MailClassifier.trusted()` | call | `src/mailtg_bridge/mail_in.py:parse_inbound`; `src/mailtg_bridge/mail_in.py:MailClassifier.trusted` | Нормализует письмо, убирает quote-tail и проверяет U→B. |
| 3 | 5 | -> cmp-state-store | `SQLiteStore.ledger_dialog()` | db-query | `src/mailtg_bridge/state.py:SQLiteStore.ledger_dialog` | Разрешает References/In-Reply-To строго через ledger. |
| 4 | 6 | -> cmp-tg-gateway | `TelethonGateway.post_as_user()` | external-call | `src/mailtg_bridge/telegram.py:TelethonGateway.post_as_user` | Публикует текст и получает Telegram message id. |
| 5 | 7 | -> cmp-state-store | `SQLiteStore.commit_reply()` | db-query | `src/mailtg_bridge/state.py:SQLiteStore.commit_reply` | Атомарно пишет own-echo и consume marker после ack. |

## Ветвления в коде

| Условие (из сценария) | Файл | Строка | Как реализовано |
|---|---|---|---|
| Автоответ/рассылка/чужой адрес/не B | `src/mailtg_bridge/orchestrator.py` | 73 | `MailClassifier.trusted()` → тихий `continue`. |
| Письмо является MAILTG-командой | `src/mailtg_bridge/orchestrator.py` | 75 | Ветка команды выполняется раньше reply path. |
| Родитель отсутствует в delivery ledger | `src/mailtg_bridge/orchestrator.py` | 85 | Тихий `continue`, публикации нет. |
| Мост OFF, сессия invalid или тело пусто | `src/mailtg_bridge/orchestrator.py` | 87 | Delivery gate/empty-body `continue`. |

## Обработка ошибок

| Ошибка (из сценария) | Файл | Строка | Механизм |
|---|---|---|---|
| Session invalid | `src/mailtg_bridge/orchestrator.py` | 91 | Блокирует session state и инициирует одно уведомление. |
| FloodWait/temporary Telegram error | `src/mailtg_bridge/orchestrator.py` | 92 | Пишет scoped backoff, consume marker не ставится. |

## Маппинг контракта живой эксплуатации

| Грань требования | Владелец в спецификации | Code Unit / конфигурация | Автотест | Live/e2e evidence или остаточный риск | Статус |
|---|---|---|---|---|---|
| -> fn-email-reply-to-tg/OE-LOAD | -> lp-email-reply-to-tg | `src/mailtg_bridge/mail_in.py:ImapMailbox.poll`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_mailbox_cycle` | `tests/integration/test_flows.py:test_reply_action_then_consume_and_command` | Реально используется `UID SEARCH ALL`; дедуп только логический через `consumed_mail`. | implemented |
| -> fn-email-reply-to-tg/OE-INPUT | -> scn-outbound-reply | `src/mailtg_bridge/mail_in.py:extract_reply_text`; `src/mailtg_bridge/mail_in.py:strip_quoted_tail` | `tests/unit/test_mail_in.py:test_html_reply_drops_blockquote_and_keeps_lines`; `tests/unit/test_mail_in.py:test_yandex_mobile_quote_block` | Plain/HTML и перечисленные классы quoted-tail нормализуются. | implemented |
| -> fn-email-reply-to-tg/OE-EVIDENCE | -> scn-outbound-reply | `src/mailtg_bridge/telegram.py:TelethonGateway.post_as_user`; `src/mailtg_bridge/state.py:SQLiteStore.commit_reply` | `tests/integration/test_flows.py:test_reply_action_then_consume_and_command` | Telegram ack наблюдаем, durable echo+consume создаются после него. | implemented |
| -> fn-email-reply-to-tg/OE-SOURCES | -> scn-outbound-reply | `src/mailtg_bridge/mail_in.py:MailClassifier.trusted`; `src/mailtg_bridge/state.py:SQLiteStore.ledger_dialog` | `tests/unit/test_mail_in.py:test_html_only_and_auto`; `tests/integration/test_flows.py:test_command_reply_to_notice_and_reject_unknown` | U→B/auto-loop deny реализован, но обычный reply на подтверждение не маршрутизируется: route знает только delivery ledger. | not-implemented |
| -> fn-email-reply-to-tg/OE-SECURITY | -> scn-outbound-reply | `src/mailtg_bridge/orchestrator.py:BridgeService.run_mailbox_cycle`; `src/mailtg_bridge/logging.py:JsonFormatter` | `tests/unit/test_runtime.py:test_log_redaction_and_json`; `tests/unit/test_mail_in.py:test_parse_trust_ids_and_reply_strip` | Trust predicate precedes publish; тело не логируется, секретные поля formatter редактирует. | implemented |
| -> fn-email-reply-to-tg/OE-RESILIENCE | -> scn-outbound-reply | `src/mailtg_bridge/orchestrator.py:BridgeService.record_failure`; `src/mailtg_bridge/state.py:SQLiteStore.commit_reply` | `tests/unit/test_algorithms.py:test_batch_order_links_and_backoff`; `tests/unit/test_state.py:test_action_before_consume_and_singletons` | Consume-after-action реализован, но записанный `tg:post:<dialog>` backoff никогда не проверяется через `_due()` перед повтором. | not-implemented |
| -> fn-email-reply-to-tg/OE-DELIVERY | -> api-telegram-userclient | `src/mailtg_bridge/telegram.py:TelethonGateway.post_as_user`; `src/mailtg_bridge/orchestrator.py:BridgeService.run_mailbox_cycle` | `tests/integration/test_flows.py:test_reply_action_then_consume_and_command` | Server ack и retry без consume есть; обещанный retry **по scoped backoff** не реализован. | not-implemented |

## Висячие пятна

| Тип | Грань | Что отсутствует |
|---|---|---|
| contract-gap | -> fn-email-reply-to-tg/OE-SOURCES | `is_bridge_message()` признаёт notice, но reply route использует только `ledger_dialog()` и не может получить диалог из notice. |
| missing | -> fn-email-reply-to-tg/OE-RESILIENCE | Перед `post_as_user()` отсутствует `_due("tg:post:<dialog>")`; сохранённый backoff не ограничивает повторы. |
| missing | -> fn-email-reply-to-tg/OE-DELIVERY | По той же причине повтор происходит каждый mailbox-такт, а не в заявленный срок scoped backoff. |

## Связи
- Сценарий: -> scn-outbound-reply
- Алгоритмы: -> alg-dedup-idempotency, -> alg-backoff-on-floodwait
- Компоненты: -> cmp-bridge-orchestrator, -> cmp-email-in, -> cmp-state-store, -> cmp-tg-gateway

