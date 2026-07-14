---
type: api
slug: api-mailbox-imap-smtp
scope: external
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
sidecar_format: asyncapi-2.x
sidecar: api-mailbox-imap-smtp.asyncapi.yaml
produced_by: migrate
---
# API: Ящик моста B — исходящая (SMTP) и входящая (IMAP) почта

<!-- Usage-контракт почтового аккаунта B, как его ПОТРЕБЛЯЕТ мост (провайдер-нейтрально, -> nfr-portability).
     Модель двух ящиков: отправка/опрос —
     ящик B; адресат доставки и доверенный отправитель — адрес U (-> rules-control). -->

## Business-reject codes
- **Business-reject codes:** N/A — контракт провайдера не содержит отдельных синхронных
  бизнес-кодов отказа; полная таксономия отказов исчерпана транспортной таблицей ниже
  (transient | auth-failed | size-rejected | rate-limit).

## Тип API
external-async (почтовый обмен: отправка по SMTP, опрос входящих по IMAP; доставка асинхронна).

## Назначение
Доставка bridged-писем и служебных писем с ящика B на адрес U и опрос ящика B на ответы и команды.
Потребители — -> cmp-email-out (SMTP produce) и -> cmp-email-in (IMAP consume).

## Машинная спецификация
Разделы «Операции / события» и «Контракт» (операции, вход/выход/ошибки) вынесены в машинный сайдкар
`api-mailbox-imap-smtp.asyncapi.yaml` (AsyncAPI 2.x; природа контракта — event-driven: SMTP produce,
IMAP consume-поллинг, -> patterns/sidecar-formats.md). Операции: `send-mail` [produce], `poll-mail`
[consume], `mark-consumed` [produce], `send-notice` [produce] — операционные идентификаторы перенесены as-is.

Типы полей контракта восстановлены из кода mailtg и data-config (детали в сайдкаре + migration-report.md §6).
Owner-decisions по нематериализованным полям закрыты (14.07, «отражение кода»):
- `accepted` (успех send-mail) и `consumed` (успех mark-consumed) — убраны: код не строит объект результата,
  успех = отсутствие исключения (send-mail несёт только `message_id`; mark-consumed — void);
- `notices[]` — вынесен из `send-mail` в отдельную операцию `send-notice` (`subject, body → message_id`),
  как в коде (`send_notice()` — отдельный вызов, не коллекция в запросе).

mark-consumed: вход разрешён фактом кода — реальный вызывающий (orchestrator) всегда передаёт только `uid`
(IMAP UID); `message_id` как ключ потребления нигде не используется → `required: [uid]` в сайдкаре (не XOR).

Параметры такта poll-mail (`mailbox=B` обяз., `consumed_set`) фиксируются в компаньоне: AsyncAPI subscribe
не имеет слота «вход» — это норма формата (параметры такта — не полезная нагрузка сообщения), отдельная
машинная проекция не нужна.

## Маппинги полей
- from ← -> data-bridge-store / Конфигурация.B_address — аккаунт-отправитель (ящик моста).
- to ← -> data-bridge-store / Конфигурация.U_address — адрес назначения (единственный доверенный).
- subject ← тег источника (из типа источника + диалога, -> dict-source-type, -> data-bridge-store); для
  служебных писем — тип уведомления (подтверждение вкл/выкл | сессия недействительна).
- message_id ← устойчивый идентификатор, порождаемый при отправке → -> data-bridge-store / Запись связки.message_id.
- in_reply_to (bridged, исходящее) ← отсутствует (новое письмо-корень треда диалога).
- Идентичность ответа (входящее): parent ← in_reply_to → поиск в журнале связки (-> data-bridge-store) → dialog_id.
- Доверие (входящее): sender=U ← сверка from с U_address; on-B ← delivered_to/to = B_address; is-reply ←
  наличие записи связки по in_reply_to; token ← subject (при сконфигурированном секрет-токене). Предикат — -> rules-control.
- html_body/text_body/inline_images/attachments/notices ← результат формирования -> cmp-email-out
  (-> alg-oversize-degrade, -> dict-media-disposition).

## Ограничения
- идемпотентность: poll-mail и чтение — идемпотентны. send-mail НЕ идемпотентна (повтор = второе письмо) —
  повторная доставка предотвращается дисциплиной курсора выше (-> alg-batch-per-dialog-cycle), не почтой.
  mark-consumed идемпотентна (повторная отметка — no-op).
- SLA: best-effort (-> nfr-operability); доставка почты асинхронна, времени доставки контракт не гарантирует.
- ретраи и их безопасность: transient IMAP/SMTP — повтор с отступом (-> alg-backoff-on-floodwait); send
  повторяется только при неподтверждённой отправке (курсор не продвинут); consume ставится после действия.
- ограничения по нагрузке: лимит размера письма провайдера (конфигурируем) → деградация -> alg-oversize-degrade,
  без молчаливого срыва; возможные rate-limit провайдера трактуются как transient.
- версионирование: контракт провайдер-нейтрален (адрес/порт/креды из конфигурации, -> nfr-portability);
  смена провайдера/аккаунта — правкой конфигурации, без изменения кода (-> nfr-deployability NFR-DEPLOY-02).

## Поведение во времени (interface-behavior guardrail)
### Таблица ошибок
| Класс ошибки | Retryable? | Терминальная? | Реакция моста |
|---|---|---|---|
| transient (SMTP/IMAP: сеть/таймаут/врем. отказ) | да, с отступом | нет | отступ, повтор на следующем такте; курсор/consume не двигаются |
| auth-failed (креды B неверны) | нет | да (ошибка конфигурации) | явная ошибка старта/такта, лог без секретов (-> nfr-privacy) |
| size-rejected (письмо > лимита провайдера) | нет (как есть) | да для этого письма | предотвращается деградацией до отправки (-> alg-oversize-degrade) |
| rate-limit (провайдер троттлит отправку/опрос) | да, с отступом (backoff) | нет | как transient: отступ и повтор на следующем такте; подтверждения/уведомления не теряются, а переотправляются (-> alg-backoff-on-floodwait) |

### Повторная доставка / повторный вызов
Входящее письмо, уже помеченное потреблённым, повторным poll не выбирается или отбрасывается по
consumed_set (-> alg-dedup-idempotency) — ответ/команда исполняются единожды. Исходящее письмо повторяется
только при недоказанной отправке (курсор не продвинут) — дубль приемлем, потеря — нет (at-least-once).
### Совместимость версий
Провайдер-нейтральность: любой SMTP/IMAP-сервер по адресу/порту/кредам. Добавление заголовков совместимо;
опора на провайдер-специфичные расширения запрещена (-> nfr-portability NFR-PORT-03).
### Лимиты и деградация
Лимит размера письма конфигурируем; превышение → деградация (крупные вложения → указание; дробление батча),
не срыв. Rate-limit → отдельный класс ошибки, трактуется как transient (retryable, backoff); подтверждения и
уведомления переотправляются, не теряются.
### Машинный sidecar
Ведётся (schema-first): `sidecar_format: asyncapi-2.x`, `sidecar: api-mailbox-imap-smtp.asyncapi.yaml`
(-> patterns/sidecar-formats.md). Типы полей восстановлены из кода/data-config; owner-decisions по
нематериализованным полям закрыты (см. раздел «Машинная спецификация» выше).

## Реализация OE-DELIVERY (обратная ссылка)
Этот API — точка подтверждения (SMTP-приём) для доставки следующих функций; контракт «доставлено» —
у владеющего сценария, здесь фиксируется только сам факт участка доставки:
- -> fn-bridge-control-by-email/OE-DELIVERY — SMTP-приём подтверждения вкл/выкл.
- -> fn-first-run-setup/OE-DELIVERY — SMTP-приём письма-уведомления «сессия недействительна».
- -> fn-dm-batch-to-email/OE-DELIVERY — SMTP-приём письма-батча личных сообщений.
- -> fn-channel-update-to-email/OE-DELIVERY — SMTP-приём письма-батча канала/группы.
- -> fn-media-in-email/OE-DELIVERY — SMTP-приём письма-батча, несущего представленные медиа.

## Связи
- Функции: -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-email-reply-to-tg, -> fn-bridge-control-by-email, -> fn-first-run-setup
- Компоненты: -> cmp-email-out, -> cmp-email-in
- Сценарии: -> scn-inbound-collect-cycle, -> scn-outbound-reply, -> scn-control-command, -> scn-session-invalid-alert
- Схема данных: -> data-bridge-store
