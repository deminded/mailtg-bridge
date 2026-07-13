---
type: test-integration
slug: tc-int-session-invalid-alert
factory: mailtg-bridge
status: draft
criticality: medium
owner: Евгений
updated: 2026-07-13
---
# Интеграционный тест: недействительная сессия — остановка, уведомление, отсутствие зацикливания

## Проверяет
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup (AC-03)
- Путь: основной (отзыв сессии в ходе работы) + ветвление «следующий такт в блокирующем состоянии»; ошибки «FloodWait без busy-loop (не session-invalid)», «peer-not-found (не session-invalid)», «сбой отправки уведомления», «отказ конфигурации при отправке уведомления»
- Грани живой эксплуатации: -> fn-first-run-setup/OE-EVIDENCE, -> fn-first-run-setup/OE-RESILIENCE, -> fn-first-run-setup/OE-DELIVERY
- Строки каталога: -> tc-flt-session-invalid-alert/FLT-000, -> tc-flt-session-invalid-alert/FLT-001, -> tc-flt-session-invalid-alert/FLT-002, -> tc-flt-session-invalid-alert/FLT-003, -> tc-flt-session-invalid-alert/FLT-004

## Fidelity эксплуатационной проверки
- Источник OE-маппинга: -> scn-first-run-setup § «Реализация контракта живой эксплуатации» (AC-03, реализуется этим вспомогательным сценарием)
- Профиль / fixture / внешняя среда: заглушка -> cmp-tg-gateway умеет вернуть класс ошибки «сессия недействительна/отозвана», «FloodWait(wait_seconds)» и «peer-not-found»; SMTP-заглушка ящика B (-> api-mailbox-imap-smtp) фиксирует уведомления и умеет смоделировать unavailable/auth-failed
- Fidelity: production-like
- Что реально проверяется: распознавание класса ошибки, остановка опроса, однократное уведомление, отсутствие busy-loop при FloodWait, отказ отправки уведомления без потери
- Residual risk: реальное время ожидания FloodWait провайдера проверяется отдельно live-e2e (-> tc-acc-deploy-and-security)

## Предварительные действия
- Мост включён; состояние сессии «действительна»; -> cmp-state-store хранит состояние сессии и флаг notified=false.

## Шаги выполнения
1. **Действие:** Запустите такт T1, на котором выборка Telegram возвращает класс «сессия недействительна».
   **Тестовые данные:** tact=T1; tg-error=session-invalid
   **Ожидаемый результат:**
   - Состояние сессии становится «недействительна»; опрос Telegram останавливается; на U отправлено одно письмо-уведомление.

2. **Действие:** Запустите такты T2 и T3 в блокирующем состоянии (тот же класс ошибки на входе не подаётся повторно).
   **Тестовые данные:** tact=T2,T3
   **Ожидаемый результат:**
   - Опрос Telegram не выполняется; повторных уведомлений нет (notified остаётся true).

3. **Действие:** Верните сессию в «действительна» через -> scn-first-run-setup и запустите следующий такт.
   **Тестовые данные:** N/A — реинициализация без нового ввода в рамках этого теста
   **Ожидаемый результат:**
   - Опрос Telegram возобновляется; notified сброшен в false (готовность снова уведомить при будущем отзыве).

4. **Действие:** Подайте серию FloodWait(wait_seconds) на выборке при действительной сессии.
   **Тестовые данные:** tg-error=FloodWait(wait_seconds=30), повтор ×3
   **Ожидаемый результат:**
   - FloodWait НЕ трактуется как session-invalid: опрос не останавливается, интервал между повторами ≥ 30 с (busy-loop отсутствует), письмо-уведомление не отправляется.

5. **Действие:** Подайте ошибку peer-not-found для одного источника при действительной сессии.
   **Тестовые данные:** tg-error=peer-not-found(source=C1)
   **Ожидаемый результат:**
   - peer-not-found НЕ трактуется как session-invalid: источник C1 пропущен, опрос по остальным источникам продолжается, письмо-уведомление не отправляется.

6. **Действие:** Подайте класс «сессия недействительна» повторно (новый такт T4) и переведите отправку уведомления в режим сбоя (SMTP-транзиент).
   **Тестовые данные:** tact=T4; tg-error=session-invalid; notice-send-mode=unavailable
   **Ожидаемый результат:**
   - Уведомление НЕ считается отправленным (notified остаётся false); повтор отправки уведомления допускается на следующем такте; состояние остаётся блокирующим.

7. **Действие:** Верните отправку уведомления в режим auth-failed (ошибка конфигурации ящика B) на следующем такте T5.
   **Тестовые данные:** tact=T5; notice-send-mode=auth-failed
   **Ожидаемый результат:**
   - Явная ошибка такта, лог без секретов; уведомление не отправлено (notified остаётся false); повтор по тому же правилу на следующем такте.

8. **Действие:** Проверьте диагностический журнал по идентификатору операции и окну времени для тактов T1, T4 и T5.
   **Тестовые данные:** correlation-id=int-session-001; time-window=10 минут; expected-event=session-invalid-detected|notice-retry-scheduled
   **Ожидаемый результат:**
   - Найдена ровно одна запись `session-invalid-detected` (T1) со статусом `blocking`; записи `notice-retry-scheduled` для T4 и T5 со статусами `pending` и специфицированными причинами (`unavailable`, `auth-failed`).

## Проверяемые условия
- Число писем-уведомлений о недействительной сессии = 1 после T1 (до отправки уведомления не удаётся на T4/T5).
- Опрос Telegram не производится в блокирующем состоянии (T2, T3), кроме подтверждённо-неопасных классов (FloodWait, peer-not-found — шаги 4–5).
- Возврат в «действительна» возможен только через -> scn-first-run-setup (шаг 3).
- При FloodWait и peer-not-found busy-loop отсутствует и session-invalid-alert НЕ срабатывает ошибочно; потерянных сообщений = 0.

## Чек-лист соответствия tc
- [x] Название краткое, без нумерации, отражает путь сценария.
- [x] criticality medium согласована с fn-first-run-setup (medium), не понижена.
- [x] Кейс основан только на scn-session-invalid-alert и tc-flt-session-invalid-alert, без домысла.
- [x] Предусловия атомарны; каждый шаг содержит действие, testData и expectedResult.
- [x] Отказные шаги (4, 5, 6, 7) ссылаются на -> tc-flt-session-invalid-alert/FLT-001, FLT-002, FLT-003, FLT-004.
- [x] Отдельная проверка логов с correlation-id/окном/событием — шаг 8.
- [x] Логи дополняют -> fn-first-run-setup/OE-EVIDENCE, а не заменяют его.

## Связи
- Сценарий: -> scn-session-invalid-alert
- Функция: -> fn-first-run-setup
- Компоненты: -> cmp-tg-gateway, -> cmp-state-store, -> cmp-bridge-orchestrator, -> cmp-email-out
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
- Каталог отказов: -> tc-flt-session-invalid-alert
