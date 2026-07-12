---
type: test-integration
slug: tc-int-session-invalid-alert
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
---
# Интеграционный тест: недействительная сессия — остановка, уведомление, отсутствие зацикливания

## Проверяет
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup (AC-03)
- Путь: основной (отзыв сессии в ходе работы) + ветвление «следующий такт в блокирующем состоянии» + ошибка «FloodWait без busy-loop»

## Предусловия
Мост включён; состояние сессии «действительна». Заглушка -> cmp-tg-gateway умеет вернуть класс ошибки
«сессия недействительна/отозвана» и «FloodWait(wait_seconds)»; SMTP-заглушка ящика B фиксирует уведомления;
-> cmp-state-store хранит состояние сессии и флаг notified.

## Входные данные
На такте T1 выборка Telegram возвращает «сессия недействительна». На тактах T2, T3 — тот же класс ошибки.
Отдельный прогон: серия FloodWait(wait_seconds) на выборке.

## Шаги
1. Запустить такт T1; распознать класс «сессия недействительна». — компонент: -> cmp-tg-gateway/cap-surface-session-errors
2. Установить состояние сессии «недействительна», остановить опрос. — -> cmp-state-store/cap-manage-session-health, -> cmp-bridge-orchestrator/cap-enforce-delivery-gates
3. Отправить однократное уведомление на U. — -> cmp-email-out/cap-send-notice
4. Запустить такты T2, T3 в блокирующем состоянии. — -> cmp-bridge-orchestrator/cap-run-inbound-cycle
5. Отдельный прогон: инъекция серии FloodWait, измерить интервалы между повторами. — -> cmp-bridge-orchestrator/cap-apply-backoff

## Ожидаемые эффекты
- После T1: состояние сессии «недействительна», опрос Telegram остановлен, одно письмо-уведомление на U.
- На T2, T3: опрос не выполняется, повторных уведомлений нет (notified=true).
- При серии FloodWait: интервал между повторами ≥ заданного отступа (нет busy-loop), сообщений не потеряно.

## Проверяемые условия
- Число писем-уведомлений о недействительной сессии = 1 (несмотря на повторные такты).
- Опрос Telegram не производится в блокирующем состоянии.
- Возврат в «действительна» возможен только через повторную инициализацию (-> scn-first-run-setup).
- При FloodWait busy-loop отсутствует; потерянных сообщений = 0.

## Связи
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup
- Компоненты: -> cmp-tg-gateway, -> cmp-state-store, -> cmp-bridge-orchestrator, -> cmp-email-out
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
