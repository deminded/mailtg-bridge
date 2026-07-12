---
type: verify-response
factory: mailtg-bridge
layer: req
responds_to: verify-report-req-glm.md
status: draft
owner: Евгений
date: 2026-07-12
---
# Ответ на blind-verify GLM: слой требований mailtg-bridge

Оркестратор (Арет) сверил находки GLM с артефактами перед сворачиванием. Свёрнуты ТОЛЬКО req-level
пункты, подтверждённые сверкой; MISREAD-и GLM понижены, HOW-детали отданы спецификации. Дельта
минимальна и трассируема (см. route-run-evolve.md, секцию «Fold GLM blind-verify»).

Легенда: **ACCEPTED** — свёрнуто в артефакт(ы); **DOWNGRADED** — не дефект/misread, не свёрнуто, с
обоснованием; **DEFERRED-TO-SPEC** — WHAT уже в req, HOW/значение уходит на слой спецификации/конфиг.

## Критические

### CRIT-001 — FloodWait / transient IMAP/SMTP — **ACCEPTED**
Свёрнуто как требование устойчивости (WHAT): толерантность к Telegram FloodWait и преходящим ошибкам
IMAP/SMTP без потери сообщений и без плотного цикла (back off, продолжить на следующем такте,
at-least-once).
- `nfr-operability.md` — NFR-OPS-06 (индикатор: потерь=0 И нет busy-loop при инъекции ошибок).
- `rules-integrity.md` — инж-правило толерантности к сбоям.
- HOW (алгоритм отступа/лимиты) → слой спецификации (явно помечено «алгоритм отступа — спека»).

### CRIT-002 — Session revoked state — **ACCEPTED**
- `cdm-bridge.md` — новая сущность «Состояние сессии» + отдельная state-матрица «действительна ↔
  недействительна/отозвана» с блокирующим (терминальным до реинициализации) состоянием; инвариант;
  атрибут конфигурации/состояния.
- `fn-first-run-setup.md` — исключительный поток + AC-03: при недействительной/отозванной сессии
  опрос ОСТАНАВЛИВАЕТСЯ, пользователю U уходит письмо-уведомление, зацикливания на той же ошибке нет.
- `00-glossary.md` — «Мост выключен/включён» размежёван с состоянием сессии (здоровье, не переключатель).

### CRIT-003 — «Auth trust fragmented» — **DOWNGRADED (центрирование) + ACCEPTED (остаток)**
DOWNGRADED: предикат доверия УЖЕ централизован и корректен в `rules-control` (отправитель=U ∧ пришло
на B ∧ in-reply-to доставленного). Утверждение GLM «fn-email-reply-to-tg AC-04 проверяет только
sender≠U и не требует in-reply-to» — MISREAD: негативный AC-04 покрывает «чужой адрес/не B», а
in-reply-to задан предусловием + шагом 2 fn и каноническим предикатом rules-control. «Re-centralize»
НЕ выполняется (создало бы дубль D-DUP).
ACCEPTED (остаток):
- (a) replay/идемпотентность приёма — ответ-письмо потребляется единожды, повторный опрос/перезапуск
  не публикует повторно: `rules-integrity.md` (правило), `cdm-bridge.md` (инвариант + строки матрицы:
  «тот же ответ» vs «новый ответ»), `fn-email-reply-to-tg.md` (альт-поток + AC-05),
  `tc-acc-antiloop-dedup.md` (шаг+ожидание).
- (b) token-validation AC — при сконфигурированном секрет-токене отсутствующий/неверный токен →
  команда игнорируется + лог: `fn-bridge-control-by-email.md` (исключит. поток + AC-04),
  `tc-acc-bridge-control.md` (вход/шаг/ожидание, AC-04).

### CRIT-004 — Media threshold undefined — **ACCEPTED (WHAT) + DEFERRED-TO-SPEC (значение)**
ACCEPTED: при превышении лимита размера письма провайдера — ДЕГРАДАЦИЯ (крупные вложения → указание/
опустить; при остаточном превышении — дробление батча), не молчаливый срыв; лимит ОБЯЗАН быть
конфигурируемым: `rules-delivery.md` (бизнес- и инж-правило), `fn-media-in-email.md` (исключит. поток
+ AC-05 + предусловие/постусловие), `cdm-bridge.md` (атрибут конфигурации «лимит размера письма»).
DEFERRED-TO-SPEC/config: конкретное дефолт-значение порога/лимита — конфигурация (число не выдумано).

## Мажорные

### MAJOR-001 — Private-DM «best-effort tg://» undefined — **ACCEPTED**
`rules-delivery.md` + `00-glossary.md`: для лички 1:1 jump-ссылки НЕТ, содержание доставляется без
ссылки; неоднозначный `tg://` переформулирован как best-effort-or-absent (не специфицированный формат).

### MAJOR-002 — Topic link format — **ACCEPTED**
`rules-delivery.md`: формат deep-link топика — `t.me/c/<internal_chat_id>/<topic_id>/<msg>` (приват),
`t.me/<username>/<topic_id>/<msg>` (публич). `00-glossary.md` — определение расширено топиком.

### MAJOR-003 — Antiloop detection method — **DEFERRED-TO-SPEC**
req фиксирует WHAT (анти-петля: собственное эхо не доставляется — dedup-by-identity, правило уже
присутствует в rules-integrity/cdm). Конкретный МЕТОД/алгоритм детекции эха — HOW, слой спецификации.

### MAJOR-004 — Cursor write failure — **ACCEPTED**
`cdm-bridge.md` (инвариант + строка матрицы), `rules-integrity.md` (инж-правило): если продвижение
курсора или запись связки не удались (в т.ч. при успешной отправке) — курсор НЕ продвигается, повтор
на след. такте приемлем, потеря — нет (at-least-once). `tc-acc-antiloop-dedup.md` обобщён.

### MAJOR-005 — Email size limit — **ACCEPTED**
Свёрнут совместно с CRIT-004 (см. выше): деградация + конфигурируемый лимит.

### MAJOR-006 — Ledger purge policy — **ACCEPTED**
`cdm-bridge.md` (инвариант «журнал связки ограничен политикой хранения» + атрибут конфигурации
retention), `nfr-operability.md` (NFR-OPS-07: bounded growth). WHAT bounded; HOW/граница → конфиг/спека.

### MAJOR-007 — Concurrency model — **DEFERRED-TO-SPEC**
Однопроцессный поллер / модель конкурентного доступа — проектное решение, слой спецификации, не req.

### MAJOR-008 — Token validation AC — **ACCEPTED**
Свёрнут как CRIT-003(b): fn-bridge-control-by-email AC-04 + tc-acc-bridge-control.

## Минорные

### MINOR-001 — cdm anti-loop comment confusing — **DEFERRED (тривиально, не блокирует)**
Строка «dropped → повторно ЗАПРЕЩЕНО (терминал)» корректна; косметическая переформулировка не
обязательна для spec_ready. Можно причесать на спеке/cleanup.

### MINOR-002 — NFR-OPS-03 not testable (no default interval) — **DOWNGRADED**
NFR тестируем ОТНОСИТЕЛЬНО настроенного интервала (индикатор: задержка ≤ настроенный интервал сбора +
время формирования). Дефолт интервала намеренно не фиксируется (best-effort, конфиг). Не дефект req.

### MINOR-003 — Glossary deep-link too narrow — **ACCEPTED**
`00-glossary.md` — определение расширено (топик-формы публич/приват + формулировка лички 1:1).

### MINOR-004 — adr-001 python core not referenced — **ACCEPTED**
`adr-001-python-core-reuse.md` — Контекст ссылается на существующее ядро: `channel-reader`
(Telethon-поллинг) и `de-agent-commons` (почта IMAP/SMTP, журнал связки/дедупа).

### MINOR-005 — tc-acc-dm-delivery AC-04 coverage gap — **DOWNGRADED**
AC-04 (dm: неуспешная отправка → курсор не продвинут) покрыт в `tc-acc-antiloop-dedup` (помечен
«AC-04 (dm)»), а не пропущен. Реального пробела покрытия нет; дубль-покрытие в dm-тесте не заводится.

## Итог
- Свёрнуто (ACCEPTED, с учётом 2 частичных CRIT-003/CRIT-004): 12 находок.
- Понижено (DOWNGRADED, misread/не-дефект): 3 — CRIT-003(центрирование), MINOR-002, MINOR-005.
- Отдано спецификации/конфигу (DEFERRED-TO-SPEC): 4 — MAJOR-003, MAJOR-007, CRIT-004(значение), MINOR-001.
- Новых артефактов: 0. Набор артефактов и число терминов глоссария (23) не изменились → индекс §2–6 не тронут.
- Оценка: слой req после свёртки — spec_ready (все блокеры CRIT-001..004 закрыты по WHAT; остаток HOW/значений корректно локализован на спеке/конфиге). Финальный gate — за владельцем.
