---
type: test-fault-catalog
slug: tc-flt-inbound-collect-cycle
factory: mailtg-bridge
status: draft
criticality: high
owner: Евгений
coverage: pairwise
derived_from_scenario: -> scn-inbound-collect-cycle
derived_from_apis: [-> api-telegram-userclient, -> api-mailbox-imap-smtp]
updated: 2026-07-13
---
# Каталог отказов: такт сбора входящих (Telegram → письмо-батч)

## Область
- Сценарий: -> scn-inbound-collect-cycle
- Функция: -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-media-in-email
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
- Стратегия покрытия: pairwise

## Матрица отказов
| fault-id | Точка инъекции (шаг → api) | Модус | Состояние прочих | Ожидаемый результат | Источник результата | Реализуемость | TC |
|---|---|---|---|---|---|---|---|
| FLT-000 | — | happy-path | healthy | Каждый адресованный диалог получает ровно одно письмо-батч на U; курсоры продвинуты, запись связки создана | -> scn-inbound-collect-cycle | feasible | -> tc-int-inbound-collect-cycle |
| FLT-001 | шаг 3 → -> api-telegram-userclient | unavailable | healthy | FloodWait/transient при выборке: такт для этого источника пропущен, курсор НЕ продвинут, пересбор на следующем такте без потери | -> fn-dm-batch-to-email/OE-RESILIENCE | feasible | -> tc-int-inbound-collect-cycle |
| FLT-002 | шаг 3 → -> api-telegram-userclient | tech-error | healthy | Отказ выборки из-за сессии (session-invalid) → сервис переходит к сценарию «недействительная сессия» (остановка опроса, уведомление; отдельный каталог отказов), а не молчаливый пропуск | -> api-telegram-userclient | feasible | -> tc-int-inbound-collect-cycle |
| FLT-003 | шаг 7 → -> api-telegram-userclient | tech-error | healthy | media-unavailable при скачивании вложения: письмо содержит текстовое указание о недоступном вложении, письмо всё равно доставлено (деградация, не потеря) | -> fn-media-in-email/OE-RESILIENCE | feasible | -> tc-int-inbound-collect-cycle |
| FLT-004 | шаг 11 → -> api-mailbox-imap-smtp | unavailable | healthy | Транзиентный отказ SMTP при отправке: курсор НЕ продвинут, запись связки не создаётся; повтор без дубля на следующем такте | -> fn-dm-batch-to-email/OE-RESILIENCE | feasible | -> tc-int-inbound-collect-cycle |
| FLT-005 | шаг 11 → -> api-mailbox-imap-smtp | tech-error | healthy | size-rejected как крайний случай (лимит письма провайдера) после исчерпания деградации -> alg-oversize-degrade: курсор не продвинут для непереданной части, попытка не теряется молча | -> api-mailbox-imap-smtp | feasible | -> tc-int-inbound-collect-cycle |

## Сводка генерации
- Строк всего: 6
- Результат взят из спецификации: 6
- TC-TODO: 0
- Infeasible с причиной: 0
- Покрыто tc-int: 6
- Deferred: 0

## Чек-лист O_T
- [x] O_T1: api-telegram-userclient имеет unavailable (FLT-001) и tech-error (FLT-002/003); api-mailbox-imap-smtp имеет unavailable (FLT-004) и tech-error (FLT-005); business-reject — N/A на обоих api.
- [x] O_T2: нет одинаковой точки/модуса/состояния с разными результатами.
- [x] O_T3: pairwise удовлетворяет минимуму для criticality high (наследуется от fn-dm-batch-to-email).
- [x] O_T4: строки резолвятся в шаги 3, 7 и 11 сценария.
- [x] O_T5: derived_from_* датированы не старше scn/api-источников.
- [x] O_T6: все feasible-строки связаны с -> tc-int-inbound-collect-cycle, связь двусторонняя.

## Связи
- Сценарий: -> scn-inbound-collect-cycle
- Функция: -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-media-in-email
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
- Интеграционные тесты: -> tc-int-inbound-collect-cycle
