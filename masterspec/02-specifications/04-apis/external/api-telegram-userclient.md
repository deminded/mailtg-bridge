---
type: api
slug: api-telegram-userclient
scope: external
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
---
# API: Пользовательский клиент Telegram (usage-контракт MTProto)

<!-- Usage-контракт внешней системы, как её ПОТРЕБЛЯЕТ мост через пользовательскую сессию (Telethon,
     -> adr-001-python-core-reuse, -> adr-002-telethon-hybrid-auth). Ведётся только .md (машинный sidecar не ведётся — режим .md-only). -->

## Тип API
external-sync (RPC поверх MTProto; опрос по расписанию, не стрим).

## Назначение
Единственный контракт доступа моста к Telegram от лица пользователя: чтение диалогов/сообщений, скачивание
медиа, публикация ответа «от себя», интерактивная авторизация. Потребитель — -> cmp-tg-gateway.

## Операции / события
- list-tracked-dialogs — перечислить отслеживаемые диалоги (личка + источники из белого списка/политики).
- fetch-messages-since — выбрать сообщения диалога строго после курсора, в хронологическом порядке.
- download-media — скачать содержимое вложения сообщения.
- post-message-as-user — опубликовать текст в диалог от лица пользователя.
- authorize-interactive — первичная интерактивная авторизация (телефон → код → 2FA-пароль) → файл сессии.

## Контракт
- list-tracked-dialogs: вход {перечень источников из конфигурации} → успех {список диалогов: id, тип
  источника, username?, internal_chat_id, топики?} → отказ {session-invalid | transient}.
- fetch-messages-since: вход {dialog_id, cursor=last_id (обяз.)} → успех {упорядоченный список сообщений с
  метаданными: msg_id, sender(display_name,@username), date, text+entities(форматирование), reply_to?,
  mentioned(bool), media[]{ref,name,size,type}, out(bool)} → отказ {FloodWait(wait_seconds) | session-invalid |
  transient | peer-not-found}.
- download-media: вход {media_ref} → успех {bytes, name, size, type} → отказ {media-unavailable | FloodWait |
  transient}. media-unavailable ≠ transient: недоступное вложение помечается указанием, такт не срывается.
- post-message-as-user: вход {dialog_id, text (обяз.)} → успех {posted_msg_id} → отказ {FloodWait(wait_seconds) |
  session-invalid | transient | peer-not-found}.
- authorize-interactive: вход {phone, code, password? (при 2FA)} → успех {session-file (права 600, вне репо)} →
  отказ {bad-code | bad-password | transient}. Терминально к неверным данным: сессия не создаётся.

## Маппинги полей
- cursor (fetch) ← -> data-bridge-store / Курсор диалога.last_id — «докуда прочитан диалог».
- posted_msg_id (успех post) → набор «опубликовано мостом» (-> data-bridge-store) — вход анти-петли -> alg-dedup-idempotency.
- media_ref (download) ← media[].ref из fetch-messages-since.
- session-file (authorize) → -> data-bridge-store состояние сессии = «действительна».
- Метаданные сообщения (sender/date/entities/reply_to/mentioned/media) — источник для формирования письма
  в -> cmp-email-out (наполнение письма — контракт -> api-mailbox-imap-smtp, не здесь).

## Ограничения
- идемпотентность: fetch/list/download — идемпотентны (чтение). post-message-as-user НЕ идемпотентна на
  стороне Telegram (повторный вызов = дубликат в диалоге) — безопасность повтора обеспечивает ВЫЗЫВАЮЩИЙ
  через однократное потребление письма-ответа (отметка «потреблено» после успешного post, -> alg-dedup-idempotency).
- SLA: best-effort (поллинг, -> nfr-operability NFR-OPS-04); жёсткого времени ответа контракт не даёт.
- ретраи и их безопасность: см. таблицу ошибок ниже; повтор безопасен для чтения; для post — только под
  защитой идемпотентности вызывающего.
- ограничения по нагрузке: Telegram навязывает FloodWait с явным интервалом ожидания — уважать (-> alg-backoff-on-floodwait).
- версионирование: контракт привязан к слою MTProto клиентской библиотеки (-> adr-001-python-core-reuse); обновление
  библиотеки/слоя — совместимое, пока сохранены перечисленные операции и метаданные сообщения; смена
  механики авторизации ломает authorize-interactive (несовместимо).

## Поведение во времени (interface-behavior guardrail)
### Таблица ошибок
| Класс ошибки | Retryable? | Терминальная? | Реакция моста |
|---|---|---|---|
| FloodWait(wait_seconds) | да, не раньше wait_seconds | нет | отступ ≥ wait_seconds, такт источника пропущен, курсор не двигается |
| transient (сеть/таймаут) | да, с отступом | нет | отступ ≥ мин. интервала, повтор на следующем такте |
| session-invalid / revoked | нет | да (блокирующее до реинициализации) | -> scn-session-invalid-alert: остановить опрос, уведомить U однократно |
| peer-not-found | нет (для этого источника) | да для операции | источник пропущен, лог, курсор не двигается |
| media-unavailable | нет | да для вложения | указание «вложение недоступно», письмо доставляется |
| bad-code / bad-password | нет | да (интерактив) | явная ошибка, повтор ввода |

### Повторная доставка / повторный вызов
Чтение (fetch/list/download) повторно безопасно. Повторная публикация одного ответа предотвращается
однократным потреблением письма (-> alg-dedup-idempotency), не самим Telegram.
### Совместимость версий
Добавление новых метаданных сообщения — совместимо (мост игнорирует неизвестное). Удаление/переименование
перечисленных операций или полей метаданных — ломающее.
### Лимиты и деградация
FloodWait — единственный явный лимит частоты; деградация = отступ и перенос такта, без потери (-> alg-backoff-on-floodwait).
### Машинный sidecar
Не ведётся (режим .md-only); согласование sidecar неприменимо.

## Связи
- Функции: -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-email-reply-to-tg, -> fn-media-in-email, -> fn-first-run-setup
- Компоненты: -> cmp-tg-gateway
- Сценарии: -> scn-inbound-collect-cycle, -> scn-outbound-reply, -> scn-first-run-setup, -> scn-session-invalid-alert
- Схема данных: -> data-bridge-store
