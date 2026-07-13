---
type: test-fault-catalog
slug: tc-flt-outbound-reply
factory: mailtg-bridge
status: draft
criticality: high
owner: Евгений
coverage: pairwise
derived_from_scenario: -> scn-outbound-reply
derived_from_apis: [-> api-mailbox-imap-smtp, -> api-telegram-userclient]
updated: 2026-07-13
---
# Каталог отказов: публикация ответа из почты в Telegram

## Область
- Сценарий: -> scn-outbound-reply
- Функция: -> fn-email-reply-to-tg
- API: -> api-mailbox-imap-smtp, -> api-telegram-userclient
- Стратегия покрытия: pairwise

## Матрица отказов
| fault-id | Точка инъекции (шаг → api) | Модус | Состояние прочих | Ожидаемый результат | Источник результата | Реализуемость | TC |
|---|---|---|---|---|---|---|---|
| FLT-000 | — | happy-path | healthy | Ответ опубликован в верном диалоге Telegram от лица пользователя, письмо помечено потреблённым | -> scn-outbound-reply | feasible | -> tc-int-outbound-reply |
| FLT-001 | шаг 2 → -> api-mailbox-imap-smtp | unavailable | healthy | Такт пропущен, письма не теряются (остаются на B), повтор опроса на следующем такте | -> api-mailbox-imap-smtp | feasible | -> tc-int-outbound-reply |
| FLT-002 | шаг 2 → -> api-mailbox-imap-smtp | tech-error | healthy | Ошибка конфигурации (auth-failed, креды B неверны): явная ошибка такта, лог без секретов; такт не выполняется до исправления конфигурации | -> api-mailbox-imap-smtp | feasible | -> tc-int-outbound-reply |
| FLT-003 | шаг 6 → -> api-telegram-userclient | unavailable | healthy | Ответ НЕ помечается потреблённым; повтор публикации на следующем такте по backoff (at-least-once), без потери | -> fn-email-reply-to-tg/OE-RESILIENCE | feasible | -> tc-int-outbound-reply |
| FLT-004 | шаг 6 → -> api-telegram-userclient | tech-error | healthy | Отказ публикации из-за сессии/авторизации трактуется консервативно как session-invalid → сервис переходит к сценарию «недействительная сессия» (остановка опроса, уведомление; отдельный каталог отказов) | -> api-telegram-userclient | feasible | -> tc-int-outbound-reply |

## Сводка генерации
- Строк всего: 5
- Результат взят из спецификации: 5
- TC-TODO: 0
- Infeasible с причиной: 0
- Покрыто tc-int: 5
- Deferred: 0

## Чек-лист O_T
- [x] O_T1: оба api имеют unavailable и tech-error (FLT-001/002 для mailbox, FLT-003/004 для telegram); business-reject — N/A на обоих api.
- [x] O_T2: нет одинаковой точки/модуса/состояния с разными результатами.
- [x] O_T3: pairwise удовлетворяет минимуму для criticality high.
- [x] O_T4: строки резолвятся в шаги 2 и 6 сценария.
- [x] O_T5: derived_from_* датированы не старше scn/api-источников.
- [x] O_T6: все feasible-строки связаны с -> tc-int-outbound-reply, связь двусторонняя.

## Связи
- Сценарий: -> scn-outbound-reply
- Функция: -> fn-email-reply-to-tg
- API: -> api-mailbox-imap-smtp, -> api-telegram-userclient
- Интеграционные тесты: -> tc-int-outbound-reply
