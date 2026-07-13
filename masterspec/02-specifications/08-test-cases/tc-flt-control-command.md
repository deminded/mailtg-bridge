---
type: test-fault-catalog
slug: tc-flt-control-command
factory: mailtg-bridge
status: draft
criticality: medium
owner: Евгений
coverage: dependent-pairs
derived_from_scenario: -> scn-control-command
derived_from_apis: [-> api-mailbox-imap-smtp]
updated: 2026-07-13
---
# Каталог отказов: управление мостом письмом

## Область
- Сценарий: -> scn-control-command
- Функция: -> fn-bridge-control-by-email
- API: -> api-mailbox-imap-smtp
- Стратегия покрытия: dependent-pairs

## Матрица отказов
| fault-id | Точка инъекции (шаг → api) | Модус | Состояние прочих | Ожидаемый результат | Источник результата | Реализуемость | TC |
|---|---|---|---|---|---|---|---|
| FLT-000 | — | happy-path | healthy | Команда исполнена (состояние изменено либо идемпотентно подтверждено), подтверждение доставлено на U | -> scn-control-command | feasible | -> tc-int-control-command |
| FLT-001 | шаг 1 → -> api-mailbox-imap-smtp | unavailable | healthy | Такт пропущен, письмо-команда остаётся необработанным на B; отметка «потреблено» не ставится; обработка на следующем такте | -> api-mailbox-imap-smtp | feasible | -> tc-int-control-command |
| FLT-002 | шаг 5 → -> api-mailbox-imap-smtp | tech-error | healthy | Отправка подтверждения не удалась технически (SMTP-транзиент); повтор отправки подтверждения на следующем такте по backoff, состояние команды не теряется | -> fn-bridge-control-by-email/OE-RESILIENCE | feasible | -> tc-int-control-command |

## Сводка генерации
- Строк всего: 3
- Результат взят из спецификации: 3
- TC-TODO: 0
- Infeasible с причиной: 0
- Покрыто tc-int: 3
- Deferred: 0

## Чек-лист O_T
- [x] O_T1: -> api-mailbox-imap-smtp имеет unavailable (FLT-001) и tech-error (FLT-002); business-reject — N/A (реестр api пуст).
- [x] O_T2: нет одинаковой точки/модуса/состояния с разными результатами.
- [x] O_T3: dependent-pairs удовлетворяет минимуму для criticality medium.
- [x] O_T4: FLT-001/FLT-002 резолвятся в шаги 1 и 5 сценария соответственно.
- [x] O_T5: derived_from_* датированы не старше scn/api-источников.
- [x] O_T6: все feasible-строки связаны с -> tc-int-control-command, связь двусторонняя.

## Связи
- Сценарий: -> scn-control-command
- Функция: -> fn-bridge-control-by-email
- API: -> api-mailbox-imap-smtp
- Интеграционные тесты: -> tc-int-control-command
