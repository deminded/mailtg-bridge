---
type: api
slug: api-mailbox-imap-smtp
scope: external
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
---
# API: Ящик моста B — исходящая (SMTP) и входящая (IMAP) почта

<!-- Usage-контракт почтового аккаунта B, как его ПОТРЕБЛЯЕТ мост (провайдер-нейтрально, -> nfr-portability).
     Ведётся только .md (машинный sidecar не ведётся — режим .md-only). Модель двух ящиков: отправка/опрос —
     ящик B; адресат доставки и доверенный отправитель — адрес U (-> rules-control). -->

## Тип API
external-async (почтовый обмен: отправка по SMTP, опрос входящих по IMAP; доставка асинхронна).

## Назначение
Доставка bridged-писем и служебных писем с ящика B на адрес U и опрос ящика B на ответы и команды.
Потребители — -> cmp-email-out (SMTP produce) и -> cmp-email-in (IMAP consume).

## Операции / события
- send-mail [produce] — отправить письмо (батч / подтверждение / уведомление) с B на U по SMTP.
- poll-mail [consume] — выбрать новые (не потреблённые) письма на ящике B по IMAP.
- mark-consumed [produce] — зафиксировать письмо обработанным (не выбирать повторно).

## Контракт
- send-mail: вход {from=B (обяз.), to=U (обяз.), subject(с тегом источника, обяз.), message_id(устойчивый,
  обяз.), in_reply_to?(нет для нового bridged-письма), html_body(обяз.), text_body(обяз.), inline_images[],
  attachments[], notices[]} → успех {accepted, message_id (для записи связки)} → отказ {transient(SMTP) |
  auth-failed | size-rejected}. size-rejected предупреждается заранее деградацией (-> alg-oversize-degrade).
- poll-mail: вход {mailbox=B (обяз.), consumed_set} → успех {список писем: uid, from, delivered_to(=B?),
  in_reply_to?, references?, subject, text_body} → отказ {transient(IMAP) | auth-failed}.
- mark-consumed: вход {uid | message_id (обяз.)} → успех {consumed} → отказ {transient}.

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

### Повторная доставка / повторный вызов
Входящее письмо, уже помеченное потреблённым, повторным poll не выбирается или отбрасывается по
consumed_set (-> alg-dedup-idempotency) — ответ/команда исполняются единожды. Исходящее письмо повторяется
только при недоказанной отправке (курсор не продвинут) — дубль приемлем, потеря — нет (at-least-once).
### Совместимость версий
Провайдер-нейтральность: любой SMTP/IMAP-сервер по адресу/порту/кредам. Добавление заголовков совместимо;
опора на провайдер-специфичные расширения запрещена (-> nfr-portability NFR-PORT-03).
### Лимиты и деградация
Лимит размера письма конфигурируем; превышение → деградация (крупные вложения → указание; дробление батча),
не срыв. Rate-limit → как transient.
### Машинный sidecar
Не ведётся (режим .md-only); согласование sidecar неприменимо.

## Связи
- Функции: -> fn-dm-batch-to-email, -> fn-channel-update-to-email, -> fn-email-reply-to-tg, -> fn-bridge-control-by-email, -> fn-first-run-setup
- Компоненты: -> cmp-email-out, -> cmp-email-in
- Сценарии: -> scn-inbound-collect-cycle, -> scn-outbound-reply, -> scn-control-command, -> scn-session-invalid-alert
- Схема данных: -> data-bridge-store
