---
type: scenario
slug: scn-inbound-collect-cycle
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
---
# Сценарий: Такт сбора входящих (Telegram → письмо-батч)

<!-- Коллапс лаконичности: один сценарий покрывает fn-dm-batch-to-email, fn-channel-update-to-email и
     fn-media-in-email — порядок кооперации компонентов один, различие «личка/канал» — ветвление гейта,
     медиа — ветвление формирования. См. route-run-spec «Коллапсы». -->

## Цель сценария
Реализует доставку личных сообщений и адресованных обновлений каналов/групп одним письмом на диалог за
такт, с представлением медиа. -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-media-in-email

## Триггер
Наступил такт сбора входящих (расписание, интервал «сбор»).

## Предусловия
Мост включён; сессия действительна; конфигурация валидна (белый список, политика упоминаний, порог/лимит,
адреса, интервалы).

## Последовательность шагов
1. Проверить блокирующие гейты (мост включён И сессия действительна). -> cmp-bridge-orchestrator/cap-enforce-delivery-gates
2. Прочитать курсоры отслеживаемых диалогов и конфигурацию. -> cmp-state-store/cap-manage-cursor, -> cmp-state-store/cap-read-config
3. Выбрать новые сообщения каждого диалога после курсора. -> cmp-tg-gateway/cap-fetch-since-cursor · -> api-telegram-userclient
4. Отсеять собственное эхо моста (анти-петля). -> cmp-tg-gateway/cap-detect-own-echo
5. Применить гейт адресованности к каждому сообщению. -> cmp-tg-gateway/cap-apply-addressing-gate · -> alg-addressing-gate
6. Сгруппировать прошедшие гейт сообщения диалога за такт в один батч (хронологически). -> cmp-bridge-orchestrator/cap-assemble-dialog-batch · -> alg-batch-per-dialog-cycle
7. Скачать вложения сообщений батча. -> cmp-tg-gateway/cap-download-media · -> api-telegram-userclient
8. Сформировать HTML-письмо: автор, время, форматирование, цитата-ответ, глубокая ссылка. -> cmp-email-out/cap-compose-batch-email, -> cmp-email-out/cap-build-deeplink
9. Представить медиа (инлайн-изображение / файл / указание). -> cmp-email-out/cap-render-media
10. Проверить лимит размера письма и при необходимости деградировать/раздробить. -> cmp-email-out/cap-degrade-on-oversize · -> alg-oversize-degrade
11. Отправить письмо(-а) с ящика B на адрес U. -> cmp-email-out/cap-send-from-b · -> api-mailbox-imap-smtp
12. Зафиксировать запись связки (Message-ID ↔ диалог) и продвинуть курсор диалога. -> cmp-state-store/cap-manage-ledger, -> cmp-state-store/cap-manage-cursor · -> alg-dedup-idempotency

## Ветвления
- Мост выключен ИЛИ сессия недействительна (шаг 1) → доставка не выполняется; при недействительной
  сессии — переход в -> scn-session-invalid-alert. Иначе → продолжить.
- Личка (шаг 5) → пропустить всегда. Канал/группа/топик → пропустить, если источник в белом списке ИЛИ
  есть упоминание (по политике); иначе → отсеять, письма нет.
- В диалоге нет прошедших гейт сообщений (шаг 6) → батч и письмо не формируются для этого диалога.
- Сообщение без вложений (шаг 9) → тело только текст. Есть изображение → инлайн. Не-изображение ≤ порога
  → файл; > порога → текстовое указание.
- Письмо в пределах лимита (шаг 10) → одно письмо. Превышает → крупные вложения в указание; при остаточном
  превышении → дробление на несколько писем (порядок сохранён).
- Вложение не скачалось (шаг 7) → в письмо помещается указание «вложение недоступно»; текст не блокируется.

## Ошибки и таймауты
- FloodWait / преходящая ошибка Telegram при выборке (шаг 3) или почты при отправке (шаг 11) → отступить,
  такт пропускается, курсор НЕ продвигается; пересбор на следующем такте без дубля. -> cmp-bridge-orchestrator/cap-apply-backoff · -> alg-backoff-on-floodwait
- Отправка письма не удалась (шаг 11) → запись связки не создаётся, курсор не продвигается (шаг 12 не
  выполняется) — повтор на следующем такте.
- Письмо отправлено, но запись связки/продвижение курсора не удались (шаг 12) → курсор НЕ продвигается;
  допускается повторная доставка на следующем такте (at-least-once, дубль приемлем, потеря — нет).
- Сессия отозвана в ходе выборки/скачивания → -> scn-session-invalid-alert (блокирующее, без busy-loop).

## Постусловия
Для каждого диалога с адресованными сообщениями — одно письмо-батч на U, запись связки, продвинутый
курсор; неадресованное отсеяно без письма; собственное эхо не доставлено; дублей нет.

## Реализация контракта живой эксплуатации
| Грань | Владелец |
|---|---|
| -> fn-dm-batch-to-email/OE-LOAD | -> lp-dm-batch-to-email |
| -> fn-dm-batch-to-email/OE-INPUT | этот сценарий |
| -> fn-dm-batch-to-email/OE-EVIDENCE | этот сценарий |
| -> fn-dm-batch-to-email/OE-SOURCES | этот сценарий |
| -> fn-dm-batch-to-email/OE-SECURITY | этот сценарий |
| -> fn-dm-batch-to-email/OE-RESILIENCE | этот сценарий |
| -> fn-dm-batch-to-email/OE-DELIVERY | -> api-mailbox-imap-smtp |
| -> fn-channel-update-to-email/OE-LOAD | -> lp-channel-update-to-email |
| -> fn-channel-update-to-email/OE-INPUT | этот сценарий |
| -> fn-channel-update-to-email/OE-EVIDENCE | этот сценарий |
| -> fn-channel-update-to-email/OE-SOURCES | этот сценарий |
| -> fn-channel-update-to-email/OE-SECURITY | этот сценарий |
| -> fn-channel-update-to-email/OE-RESILIENCE | этот сценарий |
| -> fn-channel-update-to-email/OE-DELIVERY | -> api-mailbox-imap-smtp |
| -> fn-media-in-email/OE-LOAD | -> lp-media-in-email |
| -> fn-media-in-email/OE-INPUT | этот сценарий |
| -> fn-media-in-email/OE-EVIDENCE | этот сценарий |
| -> fn-media-in-email/OE-SECURITY | этот сценарий |
| -> fn-media-in-email/OE-RESILIENCE | этот сценарий |
| -> fn-media-in-email/OE-DELIVERY | -> api-mailbox-imap-smtp |

<!-- OE-CONTROL — N/A во всех трёх функциях (не парсят управляющую грамматику); OE-SOURCES — N/A в
     fn-media-in-email (адресованность решена выше по потоку) — не входят в таблицу реализации. -->

## Проверка
- Интеграционный тест: -> tc-int-inbound-collect-cycle

## Связи
- Функция АС/ФП: -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-media-in-email
- Участвующие компоненты: -> cmp-bridge-orchestrator, -> cmp-tg-gateway, -> cmp-email-out, -> cmp-state-store
- Алгоритмы: -> alg-addressing-gate, -> alg-batch-per-dialog-cycle, -> alg-oversize-degrade, -> alg-dedup-idempotency, -> alg-backoff-on-floodwait
- API: -> api-telegram-userclient, -> api-mailbox-imap-smtp
- Профили нагрузки: -> lp-dm-batch-to-email, -> lp-channel-update-to-email, -> lp-media-in-email
- Каталог отказов: -> tc-flt-inbound-collect-cycle
