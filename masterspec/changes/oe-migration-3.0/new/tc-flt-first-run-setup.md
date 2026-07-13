---
type: test-fault-catalog
slug: tc-flt-first-run-setup
factory: mailtg-bridge
status: draft
criticality: medium
owner: Евгений
coverage: dependent-pairs
derived_from_scenario: -> scn-first-run-setup
derived_from_apis: [-> api-telegram-userclient]
updated: 2026-07-13
---
# Каталог отказов: первичная авторизация Telegram

## Область
- Сценарий: -> scn-first-run-setup
- Функция: -> fn-first-run-setup
- API: -> api-telegram-userclient
- Стратегия покрытия: dependent-pairs

## Матрица отказов
| fault-id | Точка инъекции (шаг → api) | Модус | Состояние прочих | Ожидаемый результат | Источник результата | Реализуемость | TC |
|---|---|---|---|---|---|---|---|
| FLT-000 | — | happy-path | healthy | Файл сессии создан (права 600, вне репозитория), фоновый сервис далее стартует headless | -> scn-first-run-setup | feasible | -> tc-int-first-run-setup |
| FLT-001 | шаг 2 → -> api-telegram-userclient | unavailable | healthy | Авторизация не завершается (сервис Telegram недоступен/transient), файл сессии не создаётся; явная ошибка и предложение повторить | -> api-telegram-userclient | feasible | -> tc-int-first-run-setup |
| FLT-002 | шаг 2 → -> api-telegram-userclient | tech-error | healthy | Неверный код/пароль (bad-code/bad-password, терминально к вводу): авторизация не завершается, файл сессии не создаётся; явная ошибка с предложением повторить ввод | -> fn-first-run-setup/OE-EVIDENCE | feasible | -> tc-int-first-run-setup |

## Сводка генерации
- Строк всего: 3
- Результат взят из спецификации: 3
- TC-TODO: 0
- Infeasible с причиной: 0
- Покрыто tc-int: 3
- Deferred: 0

## Чек-лист O_T
- [x] O_T1: -> api-telegram-userclient имеет unavailable (FLT-001) и tech-error (FLT-002); business-reject — N/A (реестр api пуст).
- [x] O_T2: нет одинаковой точки/модуса/состояния с разными результатами.
- [x] O_T3: dependent-pairs удовлетворяет минимуму для criticality medium.
- [x] O_T4: FLT-001/FLT-002 резолвятся в шаг 2 сценария.
- [x] O_T5: derived_from_* датированы не старше scn/api-источников.
- [x] O_T6: все feasible-строки связаны с -> tc-int-first-run-setup, связь двусторонняя.

## Связи
- Сценарий: -> scn-first-run-setup
- Функция: -> fn-first-run-setup
- API: -> api-telegram-userclient
- Интеграционные тесты: -> tc-int-first-run-setup
