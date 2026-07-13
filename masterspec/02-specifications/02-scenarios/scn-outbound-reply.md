---
type: scenario
slug: scn-outbound-reply
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
notation: yaml-graph
produced_by: migrate
---
# Сценарий: Публикация ответа из почты в Telegram

## Цель сценария
Реализует публикацию ответа письмом в исходный диалог Telegram от лица пользователя. -> fn-email-reply-to-tg

## Триггер
Наступил такт опроса ящика моста B (расписание, интервал «отправка/опрос»).

## Предусловия
Мост включён; сессия действительна; на ящике B есть новые письма.

## Последовательность шагов
1. Проверить блокирующие гейты (мост включён И сессия действительна). -> cmp-bridge-orchestrator/cap-enforce-delivery-gates
2. Выбрать новые (не потреблённые) письма на ящике B. -> cmp-email-in/cap-poll-b-imap · -> api-mailbox-imap-smtp
3. Проверить предикат доверия (отправитель = U, пришло на B, in-reply-to доставленного). -> cmp-email-in/cap-authenticate-sender
4. Классифицировать письмо как ответ на bridged-письмо. -> cmp-email-in/cap-classify-message
5. По In-Reply-To найти запись связки и целевой диалог. -> cmp-email-in/cap-resolve-ledger, -> cmp-state-store/cap-manage-ledger
6. Опубликовать текст ответа в диалог от лица пользователя. -> cmp-tg-gateway/cap-post-as-user · -> api-telegram-userclient
7. Отметить письмо потреблённым (обработано единожды). -> cmp-email-in/cap-mark-consumed, -> cmp-state-store/cap-manage-consume-markers · -> alg-dedup-idempotency

## Ветвления
- Мост выключен ИЛИ сессия недействительна (шаг 1) → публикация не выполняется до включения/реинициализации.
- Предикат доверия не выполнен (шаг 3: чужой адрес / не на B / не in-reply-to) → письмо игнорируется, в
  Telegram ничего не публикуется, факт фиксируется в логе; иначе → продолжить.
- Письмо не ответ, а команда (шаг 4) → передать в -> scn-control-command; нераспознанное → игнор.
- Записи связки нет (шаг 5: не-bridged письмо) → игнор, публикации нет; иначе → продолжить.
- Ответ содержит вложения → в версии 1 публикуется только текст (вложения не пересылаются).
- Тот же ответ уже потреблён (шаг 2/7: повторный опрос/перезапуск) → повторно в Telegram не публикуется.

## Ошибки и таймауты
- FloodWait / преходящая ошибка при публикации (шаг 6) → ответ помечается недоставленным, отметка
  «потреблено» НЕ ставится; повтор на следующем такте. -> cmp-bridge-orchestrator/cap-apply-backoff · -> alg-backoff-on-floodwait
- Сессия отозвана при публикации → -> scn-session-invalid-alert (блокирующее).
- Преходящая ошибка IMAP при опросе (шаг 2) → такт пропускается, письма не теряются (остаются на B).

## Постусловия
Ответ на bridged-письмо опубликован в верном диалоге от лица пользователя и потреблён единожды; ответ на
не-bridged/недоверенное письмо не порождает публикации и зафиксирован в логе.

## Реализация контракта живой эксплуатации
| Грань | Владелец |
|---|---|
| -> fn-email-reply-to-tg/OE-LOAD | -> lp-email-reply-to-tg |
| -> fn-email-reply-to-tg/OE-INPUT | этот сценарий |
| -> fn-email-reply-to-tg/OE-EVIDENCE | этот сценарий |
| -> fn-email-reply-to-tg/OE-SOURCES | этот сценарий |
| -> fn-email-reply-to-tg/OE-SECURITY | этот сценарий |
| -> fn-email-reply-to-tg/OE-RESILIENCE | этот сценарий |
| -> fn-email-reply-to-tg/OE-DELIVERY | -> api-telegram-userclient |

<!-- OE-CONTROL — N/A в fn-email-reply-to-tg (публикуемый текст не разбирается как управляющая
     грамматика), поэтому в таблицу реализации не входит. -->

## Проверка
- Интеграционный тест: -> tc-int-outbound-reply

## Связи
- Функция АС/ФП: -> fn-email-reply-to-tg
- Участвующие компоненты: -> cmp-bridge-orchestrator, -> cmp-email-in, -> cmp-state-store, -> cmp-tg-gateway
- Алгоритмы: -> alg-dedup-idempotency, -> alg-backoff-on-floodwait
- API: -> api-mailbox-imap-smtp, -> api-telegram-userclient
- Профили нагрузки: -> lp-email-reply-to-tg
- Каталог отказов: -> tc-flt-outbound-reply
