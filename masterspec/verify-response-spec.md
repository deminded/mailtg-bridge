---
type: verify-response
factory: mailtg-bridge
layer: spec
responds_to: verify-report-spec-glm.md
status: draft
owner: Евгений
date: 2026-07-12
---
# Ответ на blind-verify GLM: слой спецификаций mailtg-bridge

Оркестратор (Арет) сверил находки GLM с артефактами перед сворачиванием. Свёрнуты ТОЛЬКО подтверждённые
сверкой пункты; read-artifact'ы GLM (файл не прочитан из-за permission) понижены; edge-case, не несущие
решений для codegen, отданы реализации. Дельта минимальна, трассируема (см. route-run-spec.md, секцию
«Fold GLM blind-verify (spec)»). Режим — ПРАВКА in-place (слой ещё draft, direct-write как в derive/req-fold).

Легенда: **ACCEPTED** — свёрнуто в артефакт(ы) слоя спецификаций; **DOWNGRADED** — не дефект / read-artifact,
не свёрнуто, с обоснованием; **DEFERRED** — edge-case без решения для codegen, отдан реализации/CI.

Граница правки: тронут ТОЛЬКО слой `02-specifications/` (status: draft). Слой `01-requirements/` —
spec_ready (заморожен); его WHAT уже несёт нужные инварианты (NFR-OPS-05 «сбой такта → без потерь/дублей»,
NFR-OPS-07 «bounded retention»), поэтому HOW (flock, oldest-first purge) свёрнут на спеке со ССЫЛКОЙ на
эти NFR, без правки замороженного слоя (см. «Решение по границе слоёв»).

## Мажорные

### MAJOR-001 — FetchMessage gap не обнаруживается — **ACCEPTED**
Свёрнуто как контракт выборки + следствие high-watermark (не gap-detection).
- `api-telegram-userclient.md` (Ограничения): fetch-messages-since возвращает id строго > cursor в
  хронологическом порядке; непрерывность НЕ гарантируется и НЕ требуется — курсор-high-watermark делает
  пропуски/удалённые id безвредными; отдельного обнаружения дыр не нужно. Привязано к MAJOR-003.

### MAJOR-002 — Состояние сессии «частично недействительна» — **ACCEPTED**
Модель оставлена бинарной (valid/invalid); расширен ТРИГГЕР перехода (консервативная единая трактовка).
- `api-telegram-userclient.md` (после таблицы ошибок): session-invalid относится к ЛЮБОЙ операции — отказ
  post-as-user из-за сессии/авторизации при рабочем fetch трактуется как session-invalid → scn-session-invalid-alert.
- `data-bridge-store.md`: сущность «Состояние сессии» — любой отказ сессии/авторизации (в т.ч. частичный) →
  недействительна; строка state-матрицы: «Telegram отклонил сессию при ЛЮБОЙ операции (опрос/скачивание/публикация)».

### MAJOR-003 — Удалённое сообщение → курсор зависает — **ACCEPTED (приоритет, correctness)**
Курсор переопределён как МОНОТОННЫЙ HIGH-WATERMARK по id, выбранным в такте; удалённые/отсутствующие id
толерируются и НИКОГДА не блокируют последующие.
- `alg-batch-per-dialog-cycle.md`: правило 5 (продвижение до макс. выбранного в такте msg_id), новое
  правило 7 (пропуски/удалённые/отсеянные id перешагиваются, непрерывность не требуется), инвариант обновлён.
- `alg-dedup-idempotency.md`: правило 1 — курсор = high-watermark, отсутствующие/удалённые id не блокируют.
- `data-bridge-store.md`: last_id = «монотонный high-watermark», строка state-матрицы курсора, явная нота
  «удалённые/отсутствующие id перешагиваются и не стопорят прогресс».

### MAJOR-004 — Rate-limit SMTP не специфицирован — **ACCEPTED**
- `api-mailbox-imap-smtp.md`: в таблицу ошибок добавлен класс rate-limit (retryable → backoff, нетерминальный,
  как transient); «Лимиты и деградация» — подтверждения/уведомления переотправляются, не теряются.

### MAJOR-005 — Non-overlapping ticks не гарантируются при краше — **ACCEPTED**
Непересечение тактов переведено из утверждения в ГАРАНТИЮ эксклюзивной блокировки.
- `cmp-bridge-orchestrator.md` (Назначение + Ответственность): сервис держит эксклюзивный flock на lock-файле;
  второй/перекрывающий запуск (в т.ч. cron/таймер ОС) не стартует, пока блокировка занята; краш освобождает
  блокировку — следующий такт продолжает без дубля/потери. Ссылки на -> nfr-operability NFR-OPS-05,
  -> nfr-deployability NFR-DEPLOY-05 (WHAT уже в req; flock — spec-level HOW, req-слой НЕ правился, см. ниже).

### MAJOR-006 — Split-update / half-committed — **ACCEPTED**
- `alg-batch-per-dialog-cycle.md`: правило 5 фиксирует ПОРЯДОК коммита СТРОГО — отправка письма → запись
  связки → продвижение курсора; реакции: сбой отправки → курсор не двигать; отправка ок, запись связки НЕ ок
  → курсор НЕ продвигать (возможна повторная доставка, приемлемый дубль, снимается дедупом); краш между
  отправкой и продвижением → ≤1 повторная доставка (at-least-once); потеря не допускается. Порядок проверок
  и инвариант согласованы.

## Минорные

### MINOR-001 — cmp-tg-gateway capabilities «не определены» — **DOWNGRADED (read-artifact)**
Не дефект. Файл `cmp-tg-gateway.md` СУЩЕСТВУЕТ (85 строк) и детализирует все 6 capabilities
(cap-fetch-since-cursor, cap-apply-addressing-gate, cap-detect-own-echo, cap-download-media, cap-post-as-user,
cap-surface-session-errors) с входами/выходами. GLM пометил «permission denied / файл не прочитан» — это
артефакт чтения GLM, а не пробел спеки. Правок нет.

### MINOR-002 — 2FA password timeout/bad — **DEFERRED**
first-run — ИНТЕРАКТИВНЫЙ разовый setup; неверный код/пароль уже покрыт (api: bad-code/bad-password —
терминально к неверным данным, повтор ввода; scn-first-run-setup — явная ошибка + предложение повторить).
Таймаут/истечение — человек повторяет команду; отдельного автомата спека не несёт. Over-engineering не заводим.

### MINOR-003 — Media partial download — **DEFERRED**
Частичная загрузка трактуется как media-unavailable (уже в контракте download-media и ветвлении scn шаг 7:
«вложение недоступно», письмо доставляется). Отдельного класса «частично» codegen не требует.

### MINOR-004 — Version-compatibility критерии — **DEFERRED**
Контракт уже фиксирует, что удаление/переименование перечисленных операций/полей — ломающее, добавление —
совместимо. «Какие метаданные обязательны» при обновлении Telethon — забота CI/реализации (pin + smoke-тест),
не спеки.

### MINOR-005 — cmp-tg-gateway «не верифицированы» — **DOWNGRADED (read-artifact)**
Дубль MINOR-001 по той же причине (файл не прочитан GLM). Файл существует и полон. Правок нет.

### MINOR-006 — Notified-flag reset при реинициализации — **ACCEPTED**
- `scn-first-run-setup.md`: шаг 4 и постусловие — при успешной (ре)инициализации сессия=действительна И
  notified=false (готовность повторно уведомить при будущем отзыве).
- `scn-session-invalid-alert.md`: ветвление реинициализации явно сбрасывает notified=false.
  (Data-матрица `data-bridge-store` уже несла строку «реинициализация → notified=false» — сценарии
  приведены к ней.)

### MINOR-007 — Retention cleanup не алгоритмизирован — **ACCEPTED (WHAT) + config (значения)**
- `data-bridge-store.md`: retention = oldest-first по возрасту ИЛИ количеству, вычищаются только РАЗРЕШЁННЫЕ
  записи (доставленная связка / потреблённое письмо / эхо-маркер за анти-петля-окном); конкретные значения
  возраста/лимита — конфигурация. Согласованность вычистки — -> alg-dedup-idempotency, bounded — NFR-OPS-07.

## Решение по границе слоёв (MAJOR-005 / MINOR-007 и упоминание nfr-*)
GLM и триаж указывают nfr-deployability/nfr-operability как со-адресатов MAJOR-005 и MINOR-007. Эти NFR
лежат в `01-requirements/` = **spec_ready (заморожен)**, а директива прогона — «править ТОЛЬКО draft-артефакты
спеки». WHAT уже присутствует на req-слое: NFR-OPS-05 (сбой такта → без потерь/дублей на рестарте) и
NFR-OPS-07 (bounded retention). Поэтому HOW (эксклюзивный flock; oldest-first purge разрешённых записей)
свёрнут на спеке (cmp-bridge-orchestrator, data-bridge-store) СО ССЫЛКОЙ на эти NFR — доменный инвариант НЕ
меняется, «немого подъёма» нет. Замороженный слой не тронут. Если владелец захочет материализовать
единственность-экземпляра явным пунктом NFR-DEPLOY (напр., NFR-DEPLOY-06 «гарантирован единственный
экземпляр / эксклюзивная блокировка») — это отдельный req-level evolve по разморозке (см. открытый вопрос).

## Итог
- Свёрнуто (ACCEPTED): 8 находок — MAJOR-001..006, MINOR-006, MINOR-007.
- Понижено (DOWNGRADED, read-artifact GLM): 2 — MINOR-001, MINOR-005 (cmp-tg-gateway существует и полон).
- Отдано реализации/CI (DEFERRED): 3 — MINOR-002 (2FA), MINOR-003 (media partial), MINOR-004 (version-compat).
- Артефактов тронуто: 8 (alg×2, data×1, cmp×1, api×2, scn×2). Новых артефактов: 0. Набор артефактов, список
  capabilities и число терминов глоссария (23) не изменились → индекс не тронут.
- Оценка: слой spec после свёртки — **codegen_ready = yes** (все 6 MAJOR закрыты по correctness/robustness;
  курсор-deadlock и at-least-once — детерминированы; single-instance гарантирован). Финальный gate — за владельцем.
