---
type: test-integration
slug: tc-int-outbound-reply
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
---
# Интеграционный тест: ответ из почты в Telegram (доверие + маршрутизация + идемпотентность)

## Проверяет
- Сценарий: -> scn-outbound-reply
- Функция: -> fn-email-reply-to-tg
- Путь: основной + ветвления «недоверенный отправитель», «нет записи связки», «повторное потребление»; ошибка «сбой публикации»

## Предусловия
Мост включён; сессия действительна. В журнале связки есть запись для bridged-письма диалога D (Message-ID=MID).
Заглушки: -> cmp-email-in подключён к IMAP-заглушке ящика B с набором писем; -> cmp-tg-gateway с
публикацией-заглушкой, фиксирующей опубликованные сообщения (и умеющей смоделировать сбой публикации).

## Входные данные
Письма на B: R1 {from=U, in_reply_to=MID, text="ответ"}; R2 {from=чужой адрес, in_reply_to=MID};
R3 {from=U, in_reply_to=неизвестный (не-bridged)}; R1' — тот же R1, попавший в опрос повторно.

## Шаги
1. Запустить такт опроса ящика. — компонент: -> cmp-bridge-orchestrator/cap-run-mailbox-cycle
2. Проверить доверие и классифицировать каждое письмо. — -> cmp-email-in/cap-authenticate-sender, -> cmp-email-in/cap-classify-message
3. Для R1 найти запись связки и опубликовать текст в диалог D. — -> cmp-email-in/cap-resolve-ledger, -> cmp-tg-gateway/cap-post-as-user
4. Отметить R1 потреблённым. — -> cmp-email-in/cap-mark-consumed, -> cmp-state-store/cap-manage-consume-markers
5. Повторно подать R1' в опрос. — -> cmp-email-in/cap-poll-b-imap
6. Отдельно: смоделировать сбой публикации для нового ответа и дать следующий такт. — -> cmp-tg-gateway/cap-post-as-user, -> cmp-bridge-orchestrator/cap-apply-backoff

## Ожидаемые эффекты
- R1 → одно сообщение в диалоге D от лица пользователя.
- R2 (чужой адрес) → публикации нет, факт в логе.
- R3 (нет записи связки) → публикации нет.
- R1' (повторный) → повторной публикации нет (потреблён единожды).
- При сбое публикации ответ не помечен потреблённым; на следующем такте публикуется без потери.

## Проверяемые условия
- Публикаций в Telegram = 1 (только R1); R2, R3, R1' не порождают публикаций.
- Маршрутизация — в диалог D по записи связки (по диалогу, не по сообщению).
- Недоверенное письмо зафиксировано в логе (без содержания тела, -> nfr-privacy).
- Отметка «потреблено» ставится только после успешной публикации.

## Связи
- Сценарий: -> scn-outbound-reply
- Функция: -> fn-email-reply-to-tg
- Компоненты: -> cmp-bridge-orchestrator, -> cmp-email-in, -> cmp-tg-gateway, -> cmp-state-store
- API: -> api-mailbox-imap-smtp, -> api-telegram-userclient
