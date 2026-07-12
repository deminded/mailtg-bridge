---
type: route-run
factory: mailtg-bridge
flow: generation
layer_or_entry: layer=spec
pass: linear
ts: 2026-07-12T18:00
---
# Route-run: mailtg-bridge / layer=spec

Отчуждаемый аудит-след прогона derive layer=spec. Вход — согласованный (spec_ready) слой требований;
выход — слой спецификаций `02-specifications/`, status: draft.

## Вход
- Слой требований `01-requirements/` (spec_ready после свёртки blind-verify GLM — см. verify-response-req.md).
- Решения: -> adr-001-python-core-reuse (Python + переиспользование ядра), -> adr-002-telethon-hybrid-auth.
- Guardrails: /home/claude-user/rbre-guardrails (пакет rbre-requirements-intake).
- Директива владельца: LEAN (высокая цена ревью) — меньше хорошо-очерченных артефактов, не 60 мелких.

## По элементам
| Элемент (slug) | Узел | Дозапросы | Оси с дефектами | Итераций |
|---|---|---|---|---|
| cmp-bridge-orchestrator | исполнение | 0 | — | 1 |
| cmp-tg-gateway | исполнение | 0 | — | 1 |
| cmp-email-out | исполнение | 0 | — | 1 |
| cmp-email-in | исполнение | 0 | — | 1 |
| cmp-state-store | исполнение | 0 | — | 1 |
| scn-inbound-collect-cycle | исполнение | 0 | — | 1 |
| scn-outbound-reply | исполнение | 0 | — | 1 |
| scn-control-command | исполнение | 0 | — | 1 |
| scn-first-run-setup | исполнение | 0 | — | 1 |
| scn-session-invalid-alert | исполнение | 0 | — | 1 |
| alg-addressing-gate | исполнение | 0 | — | 1 |
| alg-batch-per-dialog-cycle | исполнение | 0 | — | 1 |
| alg-dedup-idempotency | исполнение | 0 | — | 1 |
| alg-backoff-on-floodwait | исполнение | 0 | — | 1 |
| alg-oversize-degrade | исполнение | 0 | — | 1 |
| api-telegram-userclient | исполнение | 0 | O2 (2 shorthand adr-ссылки, починены) | 1 |
| api-mailbox-imap-smtp | исполнение | 0 | — | 1 |
| data-bridge-store | исполнение | 0 | — | 1 |
| cd-mailtg-bridge | исполнение | 0 | — | 1 |
| tc-int-inbound-collect-cycle | исполнение | 0 | — | 1 |
| tc-int-outbound-reply | исполнение | 0 | — | 1 |
| tc-int-control-command | исполнение | 0 | — | 1 |
| tc-int-session-invalid-alert | исполнение | 0 | — | 1 |

Все элементы — узлы-ИСПОЛНЕНИЯ: развилки устройства (Python-ядро, гибридная авторизация, модель двух
ящиков, батч-за-такт) уже приняты в req/ADR; на слое спецификации новых развилок, дотягивающих до
adr-/dr-, не возникло. Модель конкуренции (MAJOR-007) закрыта решением «однопроцессный поллер, такты не
пересекаются» внутри cmp-bridge-orchestrator (следствие adr-001, не отдельный ADR).

## Коллапсы ради леаности (LEAN — записано осознанно)
1. **Telegram: один шлюз вместо двух компонентов.** tg-poller (чтение) и tg-sender (публикация) из брифа
   слиты в -> cmp-tg-gateway: обе стороны идут через одну пользовательскую сессию, делят FloodWait и
   здоровье сессии, а анти-петля естественно опирается на «что мы сами опубликовали». Разнесение
   ответственностей сохранено на уровне возможностей (cap-fetch/gate/echo/download vs cap-post).
2. **Оркестратор добавлен как 5-й компонент.** Батчинг-за-такт, гейт вкл/выкл, гейт здоровья сессии и
   управление отступом — кросс-компонентные обязанности без естественного владельца; тонкий
   -> cmp-bridge-orchestrator собирает их, вместо размазывания по адаптерам. Итог — 5 компонентов (не 6).
3. **Входящий поток — один сценарий вместо трёх.** -> scn-inbound-collect-cycle покрывает
   fn-dm-batch-to-email + fn-channel-update-to-email + fn-media-in-email: порядок кооперации один,
   «личка/канал» — ветвление гейта, медиа и деградация — ветвления формирования. Даёт 5 сценариев вместо 7.
4. **Медиа-представление без отдельного алгоритма-диспозиции.** Разложение инлайн/файл/указание живёт в
   -> dict-media-disposition (req) + возможности cap-render-media; отдельный alg не заведён (тривиальная
   таблица). Нетривиальная часть (превышение лимита) вынесена в -> alg-oversize-degrade.
5. **Внешние контракты как api scope:external (2 файла), без внутренних api и без sidecar.** Реальные
   интерфейсы системы — Telegram и почта B; межкомпонентные вызовы внутрипроцессны и покрыты возможностями
   + сценариями, отдельные internal-api избыточны. Машинные sidecar (.yaml) не заведены (режим .md-only) —
   одна нормативная редакция (O0), меньше поверхности ревью.
6. **Профиль нагрузки (lp) пропущен.** Персональный однопользовательский поллер, I/O-bound, best-effort
   без SLA-контракта (-> nfr-operability NFR-OPS-04) — capacity-планирование не несёт решений. Пропуск
   осознанный; при появлении многопоточности/мультиящика — завести lp.
7. **Одна схема данных на весь домен персистентности** (-> data-bridge-store) вместо файла на сущность.
8. **4 интеграционных теста на ключевые рантайм-пути** (сбор, ответ, команда, недействительная сессия);
   first-run интерактивен и покрыт приёмочным tc-acc-deploy-and-security + сценарием scn-first-run-setup.

## Guardrails applied (пакет rbre-requirements-intake)
- **interface-behavior** (element_type=api, ТЕПЕРЬ применимо на spec): в оба api- добавлен раздел
  «Поведение во времени» — таблица ошибок (retryable?/терминальная?), поведение при повторной доставке/
  вызове, совместимость версий, лимиты+деградация, пометка о sidecar. Conformance закрыт.
- **exceptions-first** (fn/scn): у каждого сценария заполнены «Ветвления» (≥2 исхода на развилку) и
  «Ошибки и таймауты» с наблюдаемым исходом; терминальные/блокирующие состояния помечены (session-invalid,
  dropped/delivered из cdm).
- **quality-measured** (nfr/fn): на spec напрямую не порождает элементов; тесты и алгоритмы ссылаются на
  измеримые NFR (NFR-OPS-06 busy-loop, NFR-OPS-07 retention) без «голых» прилагательных.
- **formality-profile**: профиль **S (Standard)** — обычная доработка нескольких компонентов; триггеры C
  проверены и отрицательны (деньги — нет; ПДн-регуляторика — нет, приватность решается гигиеной логов;
  необратимая миграция — нет). Риск компрометации сессии учтён в -> rules-security/-> nfr-security, не
  поднимает профиль до C.

## Метрики (отчуждаемо)
- Артефактов создано: 23 (cmp×5, scn×5, alg×5, api×2, data×1, cd×1, tc-int×4) + route-run + reindex.
- точность: тронуто/в каскаде — н/п (генерация с нуля, каскада нет).
- полнота: забытых узлов = 0; каждая fn покрыта ≥1 cmp и ≥1 scn; каждый api привязан к ≥1 scn (4/4).
- немые вердикты: 0 · немые подъёмы: 0 · немые решения: 0.
- дефекты вычитки на генерации: 1 (O2 shorthand adr-ссылки) — починен в прогоне.
- критерий: codegen_ready = yes (по суждению оркестратора; финальный gate — за владельцем; фокус
  внешней вычитки — см. «Открытые вопросы»).

## Открытые вопросы человеку
- Дефолтные ЗНАЧЕНИЯ (не выдуманы, DEFERRED-TO-SPEC/config): порог вложений, лимит размера письма,
  retention журнала/маркеров, интервалы сбора/отправки, минимальный отступ backoff — задать в примере
  конфигурации при поставке (-> nfr-deployability NFR-DEPLOY-04).
- Формат хранения состояния (единый файл vs встроенное key-value) — оставлен на слой кода (dmap); на спеке
  зафиксированы лишь логические инварианты и «без шифрования» (принятый остаточный риск).
- Механизм секрет-токена команды (в теме письма) — подтвердить у владельца формат размещения токена.

## Кто принял
<!-- заполняется человеком на гейте: merge PR, кем, когда -->

## Fold GLM blind-verify (spec) (12.07): свёртка adversarially-triaged дефектов
Независимый blind-verify GLM-4 (`verify-report-spec-glm.md`, 6 MAJOR + 7 MINOR, 0 CRITICAL) сверен
оркестратором с артефактами; свёрнуты ТОЛЬКО подтверждённые пункты, read-artifact'ы GLM (cmp-tg-gateway —
permission denied) понижены, edge-case без решения для codegen отданы реализации. Полный per-finding
вердикт — `verify-response-spec.md`. Режим — ПРАВКА in-place (слой ещё draft). Новых артефактов 0; набор
артефактов, список capabilities и число терминов глоссария (23) не изменились → индекс не тронут.

### Импакт по свёрнутым пунктам
- MAJOR-003 (приоритет, correctness): курсор = монотонный high-watermark по выбранным в такте id;
  удалённые/отсутствующие id толерируются, НИКОГДА не стопорят последующие. alg-batch-per-dialog-cycle
  (правило 5/7 + инвариант), alg-dedup-idempotency (правило 1), data-bridge-store (last_id, state-матрица, нота).
- MAJOR-006 (half-committed / at-least-once): alg-batch-per-dialog-cycle правило 5 — строгий порядок коммита
  отправка → запись связки → продвижение курсора; реакции на сбой (курсор не двигать; ≤1 дубль при краше;
  потеря запрещена).
- MAJOR-005 (single-instance): cmp-bridge-orchestrator — эксклюзивный flock на lock-файле гарантирует
  непересечение тактов; краш освобождает блокировку (ссылки NFR-OPS-05 / NFR-DEPLOY-05, req не тронут).
- MAJOR-001 (fetch-непрерывность): api-telegram-userclient — контракт «id > cursor, непрерывность не
  требуется»; high-watermark делает пропуски безвредными (без gap-detection).
- MAJOR-002 (частичная недействительность сессии): api-telegram-userclient (нота у таблицы ошибок) +
  data-bridge-store (расширен триггер) — ЛЮБОЙ отказ сессии/авторизации (в т.ч. post при рабочем fetch) →
  session-invalid; модель valid/invalid остаётся бинарной.
- MAJOR-004 (rate-limit SMTP): api-mailbox-imap-smtp — отдельный класс ошибки в таблице (retryable→backoff,
  как transient); подтверждения/уведомления переотправляются.
- MINOR-006 (сброс notified): scn-first-run-setup (шаг 4 + постусловие) + scn-session-invalid-alert
  (ветвление) — реинициализация выставляет notified=false (будущий отзыв снова уведомит U).
- MINOR-007 (retention): data-bridge-store — oldest-first purge только РАЗРЕШЁННЫХ записей по возрасту/количеству;
  значения — конфиг (bounded — NFR-OPS-07).

### По элементам (fold-пасс)
| Элемент (slug) | Узел | Находки GLM | Правка | Итераций |
|---|---|---|---|---|
| alg-batch-per-dialog-cycle | правка | MAJOR-003, MAJOR-006 | high-watermark + строгий порядок коммита + правило 7/инвариант | 1 |
| alg-dedup-idempotency | правка | MAJOR-003 | правило 1 — high-watermark, пропуски не блокируют | 1 |
| data-bridge-store | правка | MAJOR-003, MAJOR-002, MINOR-007 | last_id high-watermark, триггер сессии, oldest-first retention | 1 |
| cmp-bridge-orchestrator | правка | MAJOR-005 | эксклюзивный flock, гарантия единственного экземпляра | 1 |
| api-telegram-userclient | правка | MAJOR-001, MAJOR-002 | контракт непрерывности выборки, session-invalid для любой операции | 1 |
| api-mailbox-imap-smtp | правка | MAJOR-004 | класс rate-limit в таблице ошибок (retryable→backoff) | 1 |
| scn-session-invalid-alert | правка | MINOR-006 | сброс notified=false при реинициализации | 1 |
| scn-first-run-setup | правка | MINOR-006 | шаг 4 + постусловие: notified=false | 1 |

### scope-fence (соседи без правки → вердикт)
- cmp-tg-gateway — НЕ тронут (MINOR-001/005 = read-artifact GLM): файл существует (85 строк), все 6
  capabilities детализированы с входами/выходами; пробела спеки нет.
- scn-inbound-collect-cycle — НЕ тронут: порядок коммита (шаги 11–12) и ветка half-committed уже описаны;
  каноническая механика (high-watermark, порядок фиксации) свёрнута в alg-* (анти-дубль D-DUP), сценарий
  ссылается на них.
- alg-backoff-on-floodwait — НЕ тронут: rate-limit трактуется как transient, уже в его ведении;
  дополнен только КЛАСС в таблице api-mailbox (владелец реакции — backoff — не меняется).
- cmp-state-store — НЕ тронут: capability-контур (cap-manage-cursor/ledger/session-health/consume-markers)
  неизменен; high-watermark/retention — уточнение семантики значений в data-bridge-store, не новая capability.
- cmp-email-out, cmp-email-in, scn-outbound-reply, scn-control-command, alg-addressing-gate,
  alg-oversize-degrade, cd-mailtg-bridge, tc-int-* (4) — НЕ тронуты: вне зоны свёрнутых находок
  (correctness курсора/сессии/лимитов их контрактов не меняет).
- 01-requirements/* (nfr-operability, nfr-deployability и весь req-слой) — НЕ тронут: spec_ready заморожен;
  WHAT для MAJOR-005/MINOR-007 уже есть (NFR-OPS-05/07), свёрнут HOW на спеке со ссылкой (см. verify-response-spec «Решение по границе слоёв»).
- 00-masterspec-index — НЕ тронут: набор артефактов / capabilities / счётчик терминов (23) не изменились.

### DEFERRED (зафиксировано, не свёрнуто — over-engineering не заводим)
- MINOR-002 — 2FA timeout/bad: интерактивный разовый setup, человек повторяет ввод (bad-code/bad-password уже терминален).
- MINOR-003 — частичная загрузка медиа: трактуется как media-unavailable (уже в контракте/сценарии).
- MINOR-004 — критерии version-compat: pin+smoke Telethon — забота CI/реализации, не спеки.

### Метрики (отчуждаемо)
- тронуто/в каскаде: 8/8; каждая правка трассируется на находку GLM (MAJOR/MINOR).
- свёрнуто/понижено/отдано-реализации: 8 / 2 / 3 (из 13 находок; итоги — verify-response-spec.md).
- новых артефактов: 0; немых вердиктов: 0; немых подъёмов: 0; открытых развилок (ADR): 0.
- критерий: codegen_ready = yes (по суждению оркестратора; 6/6 MAJOR закрыты) — pending human-gate.

### Открытые вопросы человеку
- Единственность-экземпляра: flock свёрнут на спеке (cmp-bridge-orchestrator) со ссылкой на NFR-OPS-05.
  Материализовать ли это отдельным req-пунктом (напр., NFR-DEPLOY-06 «эксклюзивная блокировка / единственный
  экземпляр») — требует разморозки spec_ready req-слоя; на усмотрение владельца (не блокер codegen).
- Значения retention/lock-файл/backoff-минимум — конфигурация поставки (как и прочие дефолты, см. выше).
