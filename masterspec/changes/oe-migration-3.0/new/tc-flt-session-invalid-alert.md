---
type: test-fault-catalog
slug: tc-flt-session-invalid-alert
factory: mailtg-bridge
status: draft
criticality: medium
owner: Евгений
coverage: dependent-pairs
derived_from_scenario: -> scn-session-invalid-alert
derived_from_apis: [-> api-telegram-userclient, -> api-mailbox-imap-smtp]
updated: 2026-07-13
---
# Каталог отказов: недействительная сессия — остановка и уведомление

## Область
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
- Стратегия покрытия: dependent-pairs

## Матрица отказов
| fault-id | Точка инъекции (шаг → api) | Модус | Состояние прочих | Ожидаемый результат | Источник результата | Реализуемость | TC |
|---|---|---|---|---|---|---|---|
| FLT-000 | — | happy-path | healthy | Опрос Telegram остановлен, состояние сессии «недействительна», одно письмо-уведомление отправлено на U | -> scn-session-invalid-alert | feasible | -> tc-int-session-invalid-alert |
| FLT-001 | шаг 1 → -> api-telegram-userclient | unavailable | healthy | FloodWait НЕ трактуется как session-invalid: опрос не останавливается, такт отступает ≥ wait_seconds и повторяется, курсор не двигается, письмо-уведомление НЕ отправляется | -> api-telegram-userclient | feasible | -> tc-int-session-invalid-alert |
| FLT-002 | шаг 1 → -> api-telegram-userclient | tech-error | healthy | peer-not-found (для конкретного источника) НЕ трактуется как session-invalid: источник пропущен, лог, курсор не двигается, опрос по остальным источникам продолжается | -> api-telegram-userclient | feasible | -> tc-int-session-invalid-alert |
| FLT-003 | шаг 4 → -> api-mailbox-imap-smtp | unavailable | healthy | Уведомление НЕ считается отправленным (флаг notified не установлен); повтор уведомления допускается на следующем такте ТОЛЬКО для неотправленного, без busy-loop; состояние остаётся блокирующим | -> scn-session-invalid-alert | feasible | -> tc-int-session-invalid-alert |
| FLT-004 | шаг 4 → -> api-mailbox-imap-smtp | tech-error | healthy | Ошибка конфигурации (auth-failed, креды B неверны): явная ошибка такта, лог без секретов; уведомление не отправлено, повтор на следующем такте по тому же правилу (notified не установлен) | -> api-mailbox-imap-smtp | feasible | -> tc-int-session-invalid-alert |

## Сводка генерации
- Строк всего: 5
- Результат взят из спецификации: 5
- TC-TODO: 0
- Infeasible с причиной: 0
- Покрыто tc-int: 5
- Deferred: 0

## Чек-лист O_T
- [x] O_T1: оба api имеют unavailable и tech-error (FLT-001/002 для telegram, FLT-003/004 для mailbox); business-reject — N/A на обоих api.
- [x] O_T2: нет одинаковой точки/модуса/состояния с разными результатами.
- [x] O_T3: dependent-pairs удовлетворяет минимуму для criticality medium.
- [x] O_T4: строки резолвятся в шаги 1 и 4 сценария.
- [x] O_T5: derived_from_* датированы не старше scn/api-источников.
- [x] O_T6: все feasible-строки связаны с -> tc-int-session-invalid-alert, связь двусторонняя.

## Связи
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
- Интеграционные тесты: -> tc-int-session-invalid-alert
