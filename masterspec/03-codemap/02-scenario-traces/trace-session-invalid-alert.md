---
type: scenario-trace
slug: trace-session-invalid-alert
factory: mailtg-bridge
status: draft
updated: 2026-07-13
generated: true
---
# Code Trace: недействительная сессия — остановка и уведомление

## Сценарий
- **Спецификация:** -> scn-session-invalid-alert
- **Триггер в коде:** `src/mailtg_bridge/telegram.py:classify_error` — Telegram auth/revocation errors преобразуются в `SessionInvalid`.

## Цепочка вызовов

| # | Шаг сценария | Компонент | Code Unit | Kind | Файл | Описание |
|---|---|---|---|---|---|---|
| 1 | 1 | -> cmp-tg-gateway | `classify_error()` | call | `src/mailtg_bridge/telegram.py:classify_error` | Нормализует известные auth/session errors. |
| 2 | 2 | -> cmp-state-store | `BridgeService.invalidate_session()` | call/db-query | `src/mailtg_bridge/orchestrator.py:BridgeService.invalidate_session` | Переводит valid в false и сохраняет notified=false на первом переходе. |
| 3 | 3 | -> cmp-bridge-orchestrator | `BridgeService.delivery_allowed()` | call | `src/mailtg_bridge/orchestrator.py:BridgeService.delivery_allowed` | Все следующие inbound delivery и reply публикации блокируются. |
| 4 | 4 | -> cmp-email-out | `SmtpMailer.send_notice()` | external-call | `src/mailtg_bridge/mail_out.py:SmtpMailer.send_notice` | Отправляет письмо U; только затем записываются sent notice и notified=true. |

## Ветвления в коде

| Условие (из сценария) | Файл | Строка | Как реализовано |
|---|---|---|---|
| Session уже invalid и notified=true | `src/mailtg_bridge/orchestrator.py` | 27 | Повторный notice пропускается. |
| Повторный setup успешен | `src/mailtg_bridge/setup.py` | 11 | `set_session(True, False)` вновь разрешает polling и будущий notice. |

## Обработка ошибок

| Ошибка (из сценария) | Файл | Строка | Механизм |
|---|---|---|---|
| SMTP notice временно не отправлен | `src/mailtg_bridge/orchestrator.py` | 29 | notified остаётся false, пишется backoff; последующий mailbox cycle может повторить. |

## Маппинг контракта живой эксплуатации

Сценарий не содержит собственной таблицы «Реализация контракта живой эксплуатации»: он реализует
ветку AC-03 функции -> fn-first-run-setup. Единственные относящиеся к нему APPLICABLE-грани уже
учтены ровно один раз в `trace-first-run-setup` (OE-EVIDENCE, OE-RESILIENCE, OE-DELIVERY), поэтому
дублирующие строки здесь намеренно не создаются.

| Грань требования | Владелец в спецификации | Code Unit / конфигурация | Автотест | Live/e2e evidence или остаточный риск | Статус |
|---|---|---|---|---|---|
| — | — | — | — | Нет самостоятельно владеемых OE-граней в -> scn-session-invalid-alert. | — |

## Висячие пятна

Нет дополнительных висячих пятен сверх -> trace-first-run-setup/OE-EVIDENCE и
-> trace-first-run-setup/OE-SECURITY.

## Связи
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup
- Компоненты: -> cmp-tg-gateway, -> cmp-state-store, -> cmp-bridge-orchestrator, -> cmp-email-out

