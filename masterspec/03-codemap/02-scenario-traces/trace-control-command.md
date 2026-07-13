---
type: scenario-trace
slug: trace-control-command
factory: mailtg-bridge
status: draft
updated: 2026-07-13
generated: true
---
# Code Trace: управление мостом письмом

## Сценарий
- **Спецификация:** -> scn-control-command
- **Триггер в коде:** `src/mailtg_bridge/orchestrator.py:BridgeService.run_mailbox_cycle` — такт IMAP-опроса ящика B.

## Цепочка вызовов

| # | Шаг сценария | Компонент | Code Unit | Kind | Файл | Описание |
|---|---|---|---|---|---|---|
| 1 | 1 | -> cmp-email-in | `ImapMailbox.poll()` | external-call | `src/mailtg_bridge/mail_in.py:ImapMailbox.poll` | Читает все письма INBOX через IMAP UID. |
| 2 | 2 | -> cmp-email-in | `MailClassifier.trusted()` / `SQLiteStore.is_bridge_message()` | call/db-query | `src/mailtg_bridge/mail_in.py:MailClassifier.trusted`; `src/mailtg_bridge/state.py:SQLiteStore.is_bridge_message` | Проверяет U→B и ссылку на письмо моста. |
| 3 | 3 | -> cmp-email-in | `parse_command()` | call | `src/mailtg_bridge/commands.py:parse_command` | Разбирает строгую грамматику и optional token. |
| 4 | 4, 6 | -> cmp-state-store | `SQLiteStore.set_bridge_enabled()` | db-query | `src/mailtg_bridge/state.py:SQLiteStore.set_bridge_enabled` | В одной транзакции меняет singleton-state и ставит consume marker. |
| 5 | 5 | -> cmp-email-out | `BridgeService.flush_notices()` | call | `src/mailtg_bridge/orchestrator.py:BridgeService.flush_notices` | Отправляет поставленное в очередь подтверждение и удаляет его после успеха. |

## Ветвления в коде

| Условие (из сценария) | Файл | Строка | Как реализовано |
|---|---|---|---|
| Письмо уже потреблено или U→B trust не выполнен | `src/mailtg_bridge/orchestrator.py` | 73 | `continue` до разбора команды. |
| Команда не отвечает на письмо моста | `src/mailtg_bridge/orchestrator.py` | 80 | `is_bridge_message()` и тихий `continue`. |
| Письмо не является командой | `src/mailtg_bridge/orchestrator.py` | 85 | Переход в ветку обычного ответа. |
| ON/OFF совпадает с текущим состоянием | `src/mailtg_bridge/state.py` | 130 | Идемпотентный `UPDATE` singleton и подтверждение штатным путём. |

## Обработка ошибок

| Ошибка (из сценария) | Файл | Строка | Механизм |
|---|---|---|---|
| Временная ошибка IMAP | `src/mailtg_bridge/orchestrator.py` | 70 | Запись backoff `mail:poll`, такт прекращается до mutation. |
| Временная ошибка SMTP подтверждения | `src/mailtg_bridge/orchestrator.py` | 95 | Notice остаётся в `pending_notice`, записывается scoped backoff. |

## Маппинг контракта живой эксплуатации

| Грань требования | Владелец в спецификации | Code Unit / конфигурация | Автотест | Live/e2e evidence или остаточный риск | Статус |
|---|---|---|---|---|---|
| -> fn-bridge-control-by-email/OE-LOAD | -> lp-bridge-control-by-email | `src/mailtg_bridge/orchestrator.py:BridgeService.run`; `src/mailtg_bridge/config.py:Settings.from_env` | `tests/integration/test_flows.py:test_reply_action_then_consume_and_command` | Интервал конфигурируется, но mailbox-такт исполняется последовательно после inbound-такта и независимая от его нагрузки задержка не обеспечена. | not-implemented |
| -> fn-bridge-control-by-email/OE-INPUT | -> scn-control-command | `src/mailtg_bridge/commands.py:_unwrap`; `src/mailtg_bridge/commands.py:parse_command` | `tests/unit/test_commands.py:test_command_survives_copied_formatting` | Тема/первая непустая строка и типовые форматирующие обёртки реализованы. | implemented |
| -> fn-bridge-control-by-email/OE-EVIDENCE | -> scn-control-command | `src/mailtg_bridge/orchestrator.py:BridgeService.flush_notices` | `tests/integration/test_flows.py:test_reply_action_then_consume_and_command` | Подтверждение успеха реализовано; требуемой записи причины отклонения в логах нет. | not-implemented |
| -> fn-bridge-control-by-email/OE-SOURCES | -> scn-control-command | `src/mailtg_bridge/mail_in.py:MailClassifier.trusted`; `src/mailtg_bridge/state.py:SQLiteStore.is_bridge_message` | `tests/integration/test_flows.py:test_command_reply_to_notice_and_reject_unknown` | U→B и reply-to delivery/notice проверяются deny-by-default. | implemented |
| -> fn-bridge-control-by-email/OE-SECURITY | -> scn-control-command | `src/mailtg_bridge/commands.py:parse_command`; `src/mailtg_bridge/logging.py:redact` | `tests/unit/test_commands.py:test_strict_command_and_token`; `tests/unit/test_runtime.py:test_log_redaction_and_json` | Токен сравнивается `hmac.compare_digest`, секретные поля редактируются. | implemented |
| -> fn-bridge-control-by-email/OE-RESILIENCE | -> scn-control-command | `src/mailtg_bridge/state.py:SQLiteStore.set_bridge_enabled`; `src/mailtg_bridge/locking.py:LifetimeLock.acquire` | `tests/unit/test_state.py:test_action_before_consume_and_singletons`; `tests/unit/test_runtime.py:test_lock_exclusive_and_private` | State+consume атомарны, singleton сохраняется в SQLite, второй процесс исключён lock-файлом. | implemented |
| -> fn-bridge-control-by-email/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/mail_out.py:SmtpMailer.send`; `src/mailtg_bridge/orchestrator.py:BridgeService.delivery_allowed` | `tests/integration/test_flows.py:test_reply_action_then_consume_and_command` | SMTP ack завершает подтверждение; OFF блокирует Telegram→email и email→Telegram data paths, но не команды. | implemented |
| -> fn-bridge-control-by-email/OE-CONTROL | -> scn-control-command | `src/mailtg_bridge/commands.py:parse_command` | `tests/unit/test_commands.py:test_strict_command_and_token` | Полное регистронезависимое совпадение `MAILTG ON|OFF [token]`, отклонения без mutation. | implemented |

## Висячие пятна

| Тип | Грань | Что отсутствует |
|---|---|---|
| contract-gap | -> fn-bridge-control-by-email/OE-LOAD | Нет отдельного deadline/планировщика, гарантирующего обработку команды в один mailbox-интервал независимо от длительности inbound-цикла. |
| missing | -> fn-bridge-control-by-email/OE-EVIDENCE | В ветках строк 73, 75 и 80 нет требуемого структурированного события об отклонении и его причине. |

## Связи
- Сценарий: -> scn-control-command
- Алгоритмы: -> alg-dedup-idempotency
- Компоненты: -> cmp-email-in, -> cmp-state-store, -> cmp-email-out, -> cmp-bridge-orchestrator

