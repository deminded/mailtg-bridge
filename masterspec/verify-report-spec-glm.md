<!-- GLM-4 independent blind verify of SPEC layer, 2026-07-12; via z.ai, saved by Arête -->

# ОТЧЁТ О НЕЗАВИСИМОЙ СЛЕПОЙ ВЕРИФИКАЦИИ СПЕЦИФИКАЦИИ mailtg-bridge
## Дата: 2026-07-12 | Критерий: codegen_ready (можно ли писать код БЕЗ домысла)

---

## КРАТКИЙ ВЕРДИКТ

**codegen_ready: ЧАСТИЧНО** — спецификация содержит **6 MAJOR** и **7 MINOR** дефектов, но НЕТ критических блокеров. Код можно начать писать, но потребуется домысел в указанных областях (cmp-tg-gateway capabilities, edge-case алгоритмы, детализация состояния сессии).

---

## ОСЬ O0: SINGLE-SOURCE (конфигурация и данные определены единожды)

### ✅ Проверено: data-bridge-store.md как источник истины

**Конфигурация в data-bridge-store (строки 47-52):**
- tg_access, session_path, B_imap {host, port, credentials}, B_smtp {host, port, credentials}
- U_address, whitelist, mention_policy + mention_list
- attachment_threshold, email_size_limit, retention
- collect_interval, send_interval, command_token

**Маппинги в api-telegram-userclient.md (строки 43-49):**
- cursor ← data-bridge-store/Курсор диалога.last_id ✓
- posted_msg_id → data-bridge-store «опубликовано мостом» ✓
- media_ref ← media[].ref ✓
- session-file → data-bridge-store/состояние сессии ✓

**Маппинги в api-mailbox-imap-smtp.md (строки 37-48):**
- from ← data-bridge-store/B_address ✓
- to ← data-bridge-store/U_address ✓
- subject ← тег источника ✓
- message_id → data-bridge-store/Запись связки.message_id ✓
- in_reply_to ← отсутствует ✓
- Идентичность ответа: in_reply_to → поиск в журнале связки ✓
- Доверие: sender=U, on-B, token ← subject ✓

### Вывод по O0: **ДЕФЕКТОВ НЕТ**. Single-source соблюдён, ссылки последовательны.

---

## ОСЬ O1/O2: СВЯЗНОСТЬ И ПОКРЫТИЕ (прямое и обратное)

### ✅ Покрытие функций АС/ФП сценариями и компонентами

| Функция АС/ФП | Сценарий | Компоненты в сценарии |
|---|---|---|
| fn-dm-batch-to-email | scn-inbound-collect-cycle | orch, tg-gw, email-out, state |
| fn-channel-update-to-email | scn-inbound-collect-cycle | orch, tg-gw, email-out, state |
| fn-email-reply-to-tg | scn-outbound-reply | orch, email-in, tg-gw, state |
| fn-bridge-control-by-email | scn-control-command | orch, email-in, state, email-out |
| fn-first-run-setup | scn-first-run-setup | tg-gw, state |
| fn-media-in-email | scn-inbound-collect-cycle | email-out |

### ✅ Покрытие API сценариями

| API | Сценарии использования |
|---|---|
| api-telegram-userclient | inbound-cycle, outbound-reply, first-run-setup, session-invalid-alert |
| api-mailbox-imap-smtp | inbound-cycle, outbound-reply, control-command, session-invalid-alert |

### ⚠️ MINOR-001: cmp-tg-gateway не определён как компонент-источник capabilities

**Что:** В спецификации есть ссылки на capabilities cmp-tg-gateway (cap-fetch-since-cursor, cap-detect-own-echo, cap-apply-addressing-gate, cap-download-media, cap-post-as-user, cap-surface-session-errors), но файл cmp-tg-gateway.md НЕ прочитан (доступ запрещён).

**Почему:** Файл cmp-tg-gateway.md не был доступен при чтении (permission denied). Однако по сценариям видно, что capabilities используются: inbound-cycle шаги 3,4,5,7; outbound-reply шаг 6; session-invalid-alert шаг 1.

**Артефакт:** cmp-tg-gateway.md (предполагается существование)

**Влияние:** Неизвестно, достаточно ли детализированы capabilities для codegen. По сценариям видны имена и назначения, но детали входов/выходов не подтверждены.

### Вывод по O1/O2: **1 MINOR** (cmp-tg-gateway не верифицирован).

---

## ОСЬ O4: ТРАССИРОВКА ВВЕРХ (нет висячих ссылок)

### ✅ Проверены все артефакты spec на ссылки вверх

**Компоненты → ссылки:**
- cmp-bridge-orchestrator: → fn-*, → scn-*, → alg-*, → data-* ✓
- cmp-state-store: → fn-*, → scn-*, → alg-*, → data-* ✓
- cmp-email-out: → fn-*, → scn-*, → alg-*, → api-*, → data-* ✓
- cmp-email-in: → fn-*, → scn-*, → alg-*, → api-*, → data-* ✓

**Сценарии → ссылки:**
- scn-inbound-collect-cycle: → fn-*, → cmp-*, → alg-*, → api-* ✓
- scn-outbound-reply: → fn-*, → cmp-*, → alg-*, → api-* ✓
- scn-control-command: → fn-*, → cmp-*, → alg-*, → api-* ✓
- scn-session-invalid-alert: → fn-*, → cmp-*, → alg-*, → api-* ✓
- scn-first-run-setup: → fn-*, → cmp-*, → api-* ✓

**Алгоритмы → ссылки:**
- alg-batch-per-dialog-cycle: → cmp-*, → scn-*, → rules-* ✓
- alg-backoff-on-floodwait: → cmp-*, → scn-*, → rules-* ✓
- alg-addressing-gate: → cmp-*, → scn-*, → rules-* ✓
- alg-oversize-degrade: → cmp-*, → scn-*, → rules-* ✓
- alg-dedup-idempotency: → cmp-*, → scn-*, → rules-* ✓

### Вывод по O4: **ДЕФЕКТОВ НЕТ**. Все ссылки трассируются вверх.

---

## ОСЬ O5-НЕГАТИВ: ТАКСОНОМИЯ ОШИБОК И КРАЕВЫЕ СОСТОЯНИЯ

### ✅ Таксономия ошибок Telethon (api-telegram-userclient.md)

| Класс ошибки | Retryable? | Терминальная? | Реакция |
|---|---|---|---|
| FloodWait | да (не раньше wait_seconds) | нет | отступ, такт пропущен |
| transient (сеть/таймаут) | да, с отступом | нет | отступ, повтор |
| session-invalid/revoked | нет | да (блокирующее) | остановка, уведомление U |
| peer-not-found | нет | да для операции | источник пропущен, лог |
| media-unavailable | нет | да для вложения | указание «недоступно» |
| bad-code/bad-password | нет | да (интерактив) | явная ошибка, повтор ввода |

### ✅ Таксономия ошибок IMAP/SMTP (api-mailbox-imap-smtp.md)

| Класс ошибки | Retryable? | Терминальная? | Реакция |
|---|---|---|---|
| transient (SMTP/IMAP) | да, с отступом | нет | отступ, повтор |
| auth-failed | нет | да (ошибка конфигурации) | явная ошибка старта/такта |
| size-rejected | нет | да для письма | предотвращается деградацией |

### ⚠️ MAJOR-001: Ошибка FetchMessage gap не специфицирована

**Что:** Если fetch-messages-since возвращает неполный список (break in continuity, mid-stream gap), нехватка сообщений не обнаруживается.

**Почему:** Алгоритм дедупа (alg-dedup-idempotency правило 1) проверяет только «msg_id > cursor», но не гарантирует непрерывность. Если Telegram вернул [101, 105] (пропущены 102-104), курсор сдвинется до 105, и 102-104 потеряны без обнаружения.

**Артефакт:** api-telegram-userclient.md (операция fetch-messages-since), alg-dedup-idempotency.md

**Как должно быть:** Либо требовать от fetch непрерывности (контракт), либо обнаруживать gap и запрашивать заново.

### ⚠️ MAJOR-002: Состояние сессии «частично недействительна» не специфицировано

**Что:** Если Telegram отклоняет ОПРЕДЕЛЁННЫЕ операции (например, post-message-as-user отозвана, но fetch-messages-since работает), состояние сессии неоднозначно.

**Почему:** Матрица состояний сессии (data-bridge-store строки 77-86) бинарна: «действительна» / «недействительна». Нет состояния «частично недействительна» (fetch ок, post fail). Реакция не определена.

**Артефакт:** data-bridge-store.md (состояние сессии), api-telegram-userclient.md (session-invalid при fetch vs post)

### ⚠️ MAJOR-003: Сообщение удалено/недоступно (msg_id disappeared)

**Что:** Если сообщение с msg_id > cursor было удалено из Telegram до того, как мост его обработал, курсор никогда не продвинется за него, и все последующие сообщения зависнут.

**Почему:** Правило курсора: «msg_id > cursor → доставить». Если msg_id=102 удалён, курсор останется на 101, и 103+ никогда не будут доставлены.

**Артефакт:** alg-batch-per-dialog-cycle.md, alg-dedup-idempotency.md, data-bridge-store.md (курсор)

### ⚠️ MINOR-002: 2FA пароль не успел/не подошёл

**Что:** Сценарий first-run-setup упоминает 2FA, но не специфицирована реакция на «password expired/timeout» или «bad password» (повтор ввода? блокировка?).

**Почему:** В таблице ошибок Telegram есть только bad-code/bad-password (терминально к неверным данным), но нет сценария повтора/истечения.

**Артефакт:** scn-first-run-setup.md, api-telegram-userclient.md

### ⚠️ MINOR-003: Media download частичный сбой

**Что:** Если медиа скачалось частично (bytes < size по ref), что делать? Повторить? Поместить частичное?

**Почему:** В таблице ошибок есть только media-unavailable (полностью недоступно). Частичная загрузка не покрыта.

**Артефакт:** api-telegram-userclient.md (download-media), scn-inbound-collect-cycle шаг 7

### Вывод по O5: **3 MAJOR, 2 MINOR** (таксономия в основном полная, но edge cases не все покрыты).

---

## ОСЬ O6: КОНТРАКТЫ ИНТЕРФЕЙСОВ

### ✅ Таблицы ошибок в API (покрытие по guardrail interface-behavior)

**api-telegram-userclient.md (строки 64-73):**
- FloodWait, transient, session-invalid, peer-not-found, media-unavailable, bad-code/bad-password ✓
- Retryable/терминальность указана ✓
- Реакция моста указана ✓

**api-mailbox-imap-smtp.md (строки 63-69):**
- transient, auth-failed, size-rejected ✓
- Retryable/терминальность указана ✓
- Реакция моста указана ✓

### ✅ Redelivery (повторная доставка/вызов)

**api-telegram-userclient:** post-message-as-user НЕ идемпотентна, защита через alg-dedup-idempotency ✓
**api-mailbox-imap-smtp:** send-mail НЕ идемпотентна, защита через курсор ✓

### ✅ Лимиты и деградация

**Telegram:** FloodWait → отступ ✓
**SMTP:** лимит размера → деградация (alg-oversize-degrade) ✓

### ⚠️ MAJOR-004: Лимит частоты SMTP не специфицирован

**Что:** api-mailbox-imap-smtp указывает «возможные rate-limit провайдера трактуются как transient», но нет явного лимита и деградации.

**Почему:** Rate-limit может быть не только transient, но и block. Нет явной стратегии при rate-limit SMTP (отправка подтверждений, уведомлений).

**Артефакт:** api-mailbox-imap-smtp.md (строка 59)

### ⚠️ MINOR-004: Совместимость версий частична

**Что:** В api-telegram-userclient указано «добавление метаданных — совместимо», но нет критерия «какие метаданные обязательны для работы моста».

**Почему:** Если Telethon обновится и уберет reply_to или media, мост сломается. Нет explicit compatibility statement.

**Артефакт:** api-telegram-userclient.md (строки 78-79)

### Вывод по O6: **1 MAJOR, 1 MINOR** (таблицы ошибок в порядке, но rate-limit SMTP и compat-критерии не полны).

---

## ОСЬ O7: АЛГОРИТМИЧЕСКАЯ ПОЛНОТА И CONCURRENCY

### ✅ Concurrency model (однопроцессный поллер)

**cmp-bridge-orchestrator.md (строки 15-16):**
- «Однопроцессный поллер: такты не пересекаются, состояние общее» ✓

**cmp-bridge-orchestrator.md (строки 21-27):**
- Проверка гейтов перед доставкой/публикацией ✓
- Управление отступом ✓

### ⚠️ MAJOR-005: Single-process poller non-overlapping ticks недостаточно детализирован

**Что:** «Такты не пересекаются» не специфицирует:
- Что происходит при краше процесса во время такта?
- Как гарантируется non-overlapping при перезапуске?
- Есть ли lock-файл? flock?

**Почему:** Если процесс падает после отправки письма (шаг 11 inbound-cycle) но ДО продвижения курсора (шаг 12), перезапуск через 1 секунду может начать параллельный такт. Spec не запрещает это.

**Артефакт:** cmp-bridge-orchestrator.md, scn-inbound-collect-cycle (шаги 11-12)

### ⚠️ MAJOR-006: Cursor advancement split-update race condition

**Что:** Курсор продвигается ТОЛЬКО после «успешной отправки письма И записи связки» (alg-batch-per-dialog-cycle правило 5). Но не специфицировано, что делать при:
- Успешная отправка, ОШИБКА записи связки
- ОШИБКА отправки, успешная запись связки (недопустимо по инварианту, но реакция не указана)

**Почему:** Состояние «half-committed» не определено. Курсор не продвигается, но письмо могло уйти. Дубликат? Повтор?

**Артефакт:** alg-batch-per-dialog-cycle.md (правило 5), scn-inbound-collect-cycle (шаги 11-12)

### ⚠️ MINOR-005: cmp-tg-gateway capabilities не детализированы

**Что:** Сценарии ссылаются на cap-fetch-since-cursor, cap-detect-own-echo, cap-apply-addressing-gate, cap-download-media, cap-post-as-user, cap-surface-session-errors, но детальные входы/выходы не верифицированы (файл cmp-tg-gateway.md не был доступен).

**Почему:** Для codegen нужно знать:
- cap-detect-own-echo: как детектится? (по msg_id в наборе «опубликовано мостом»? по out=true+msg_id?)
- cap-apply-addressing-gate: где решено — в tg-gw или orch?
- cap-surface-session-errors: какие классы ошибок surfaced?

**Артефакт:** cmp-tg-gateway.md (не доступен для верификации)

### ⚠️ MINOR-006: Session health notified flag обновление не детализировано

**Что:** В scn-session-invalid-alert указано «notified=true → повторного уведомления нет». Но не специфицировано:
- Когда notified устанавливается в false?
- При реинициализации (scn-first-run-setup) notified сбрасывается?

**Почему:** Если notified не сбросить при реинициализации, пользователь НЕ получит уведомление о следующем отзыве сессии.

**Артефакт:** scn-session-invalid-alert.md (ветвление), scn-first-run-setup.md (нет упоминания notified)

### ⚠️ MINOR-007: Retention cleanup not algorithmised

**Что:** data-bridge-store указывает «журнал ограничен политикой retention», но не специфицирован алгоритм вычистки.

**Почему:** Для codegen нужно знать:
- FIFO? LIFO? По timestamp?
- Как гарантируется consistent cleanup?
- Связь с consumed markers и echo markers cleanup?

**Артефакт:** data-bridge-store.md (строки 101-102), alg-dedup-idempotency.md (инвариант)

### Вывод по O7: **3 MAJOR, 3 MINOR** (concurrency model есть, но edge cases не все специфицированы).

---

## ИТОГОВАЯ СВОДКА ДЕФЕКТОВ

### CRITICAL (блокируют codegen): **0**

### MAJOR (требуют домысла при кодировании): **6**

| ID | Артефакт | Что | Почему |
|---|---|---|---|
| MAJOR-001 | api-telegram-userclient.md, alg-dedup-idempotency.md | FetchMessage gap не обнаруживается | Нет проверки непрерывности |
| MAJOR-002 | data-bridge-store.md | Состояние сессии «частично недействительна» | Бинарное состояние, частичный отказ не покрыт |
| MAJOR-003 | alg-batch-per-dialog-cycle.md | Сообщение удалено → курсор зависнет | Нет стратегии skip-deleted |
| MAJOR-004 | api-mailbox-imap-smtp.md | Rate-limit SMTP не специфицирован | Только «как transient» |
| MAJOR-005 | cmp-bridge-orchestrator.md | Non-overlapping ticks не гарантируется при краше | Нет lock-механизма |
| MAJOR-006 | alg-batch-per-dialog-cycle.md | Split-update race condition | Half-committed состояние не определено |

### MINOR (рекомендуется уточнить до кода): **7**

| ID | Артефакт | Что |
|---|---|---|
| MINOR-001 | cmp-tg-gateway.md | Capabilities не детализированы |
| MINOR-002 | scn-first-run-setup.md | 2FA password timeout/bad не специфицирован |
| MINOR-003 | api-telegram-userclient.md | Media partial download не покрыт |
| MINOR-004 | api-telegram-userclient.md | Version compatibility критерии не полны |
| MINOR-005 | cmp-tg-gateway.md | Capabilities не верифицированы |
| MINOR-006 | scn-session-invalid-alert.md | Notified flag reset не детализирован |
| MINOR-007 | data-bridge-store.md | Retention cleanup algorithm не задан |

---

## ФИНАЛЬНЫЙ ВЕРДИКТ: codegen_ready

**Ответ: ЧАСТИЧНО (с оговорками)**

### Можно ли писать код БЕЗ домысла?
- Базовая логика: **ДА** — сценарии, алгоритмы, API-контракты достаточны для каркаса
- Edge cases: **НЕТ** — требуется домысел в 6 MAJOR областях (особенно MAJOR-001/003/005/006)

### Блокеры для начала кодирования:
Критических блокеров НЕТ. Можно начинать, но:
1. MAJOR-001/003 нужно решить BEFORE кодом курсора (gap detection vs skip-deleted)
2. MAJOR-005 нужен lock-механизм или явное заявление «один процесс»
3. MAJOR-006 нужно специфицировать half-committed реакцию

### Что derive spec упустил:
1. **cmp-tg-gateway.md** — capabilities не детализированы (MINOR-001/005)
2. **Session health partial invalidity** — состояние не полно (MAJOR-002)
3. **Concurrency non-overlapping ticks** — нет lock-механизма (MAJOR-005)
4. **Retention cleanup algorithm** — не задан (MINOR-007)
5. **FetchMessage continuity** — не в контракте (MAJOR-001)
6. **Deleted message handling** — не специфицировано (MAJOR-003)

---

## РЕКОМЕНДАЦИЯ

**Spec layer: REVISION REQUIRED** — закрыть 6 MAJOR перед кодированием. После этого — codegen_ready.

**Priority:**
1. MAJOR-005 (concurrency locks) — архитектурно
2. MAJOR-006 (split-update) — критично для at-least-once
3. MAJOR-001/003 (cursor edge cases) — критично для полноты
4. MAJOR-002/004 (error taxonomy gaps) — важно для устойчивости

**После правок: повторная верификация.**
