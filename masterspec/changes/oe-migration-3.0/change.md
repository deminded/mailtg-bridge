# Change: oe-migration-3.0

> **Статус**: Реализовано (req + spec; code — следующий шаг)
>
> **Класс**: migration
>
> **Дата создания**: 2026-07-13
>
> **Автор**: Арет
>
> **Версия**: 1.0
>
> **Фабрика**: mailtg-bridge
>
> **Целевой индекс**: masterspec/00-masterspec-index.md

---

## 1. Мотивация

### 1.1. Цель изменения
Мигрировать слой требований mailtg-bridge с мета-модели 2.6 (без «периметра функции») на контракт 3.0
(OE — «Контракт живой эксплуатации»): добавить 8 обязательных граней OE на каждую внешнюю-I/O функцию,
поле `criticality` и трассировку граней из tc-acc. Транскрипция уже реализованного поведения, без домысла.

### 1.2. Инициатор
Евгений (слой 3 доработки masterspec; версионирование + миграция от состояния). Детектор дельты —
`check-operational-envelope.py`.

### 1.3. Приоритет
высокий

### 1.4. Слой(и) изменения
- [x] требования (`01-requirements/`)

### 1.5. Контекст
Первый боевой прогон контура миграции `references/migration.md` (feature-detection → дозаполнение →
сертификация). Дельта до 3.0 снята детектором: 6 внешних функций без граней OE / criticality (74 BLOCKER
на req). После сертификации req (`3.0-req`) детектор дал дельту slice спецификаций (125 BLOCKER на
`--scope spec`): OE-грани не протрассированы в `scn-` (single-source владелец слоя spec), нет `lp-` на
`OE-LOAD`, нет обратной ссылки `OE-DELIVERY` в `api-`/`context-`, нет `tc-flt-*` на сценарии с внешними
вызовами, `tc-int-*` без `criticality`/промышленного step-контракта. Второй проход того же контура,
тот же change (расширение, не новый slug).

### 1.6. Слой(и) изменения — уточнение
- [x] требования (`01-requirements/`) — выполнено ранее.
- [x] спецификации (`02-specifications/`) — выполнено этим проходом.

---

## 2. Затронутые артефакты

Миграция обогащает СУЩЕСТВУЮЩИЕ артефакты без смены slug (добавить `criticality` + секцию OE + трассы).
Фабрика — `draft`, применение — прямо в дерево с ревью по git-diff (`migration.md §3`); `new/` хранит
источник дозаполнения как аудит. Применённый `status` сохранён `draft` (migration-класс не форсит actual).

### 2.2. MIGRATED — функции (in-place, источник в `new/`)

| # | Slug | criticality | Грани |
|---|------|-------------|-------|
| 1 | fn-bridge-control-by-email | medium | 8 APPLICABLE |
| 2 | fn-dm-batch-to-email | high | 7 APPLICABLE, OE-CONTROL N/A |
| 3 | fn-channel-update-to-email | medium | 7 APPLICABLE, OE-CONTROL N/A |
| 4 | fn-email-reply-to-tg | high | 7 APPLICABLE, OE-CONTROL N/A |
| 5 | fn-first-run-setup | medium | 6 APPLICABLE, OE-SOURCES/OE-CONTROL N/A |
| 6 | fn-media-in-email | medium | 6 APPLICABLE, OE-SOURCES/OE-CONTROL N/A |

### 2.2b. MIGRATED — трассировка граней (tc-acc, in-place)

Расширение периметра: req-гейт (single-source) требует ссылку `-> fn-<slug>/OE-<ID>` из корпуса tc-acc.
Добавлены `criticality`, блок «Грани:», step-contract в 7 файлов `01-requirements/08-test-cases/tc-acc-*.md`
(bridge-control, dm-delivery, channel-gating, email-reply, deploy-and-security, media-rendering, antiloop-dedup).

### 2.3. MIGRATED — слой спецификаций (in-place, источник в `new/`)

Транскрипция тех же 41 APPLICABLE-грани в spec-слой (single-source: `scn-` владеет таблицей
реализации; `api-`/`context-`/`lp-` несут обратную ссылку, не копируют набор):

| # | Артефакт | Что добавлено |
|---|------|-------------|
| 1 | `scn-control-command.md` | Секция «Реализация контракта…» — 8 граней fn-bridge-control-by-email (OE-DELIVERY → `api-mailbox-imap-smtp`, OE-LOAD → `lp-bridge-control-by-email`); «## Проверка» → `tc-int-control-command` |
| 2 | `scn-first-run-setup.md` | 6 граней fn-first-run-setup (OE-SOURCES/OE-CONTROL N/A вне таблицы); «## Проверка» → `tc-int-first-run-setup` |
| 3 | `scn-inbound-collect-cycle.md` | 20 граней трёх функций (dm-batch 7, channel-update 7, media-in 6); «## Проверка» → `tc-int-inbound-collect-cycle` |
| 4 | `scn-outbound-reply.md` | 7 граней fn-email-reply-to-tg (OE-DELIVERY → `api-telegram-userclient`); «## Проверка» → `tc-int-outbound-reply` |
| 5 | `scn-session-invalid-alert.md` | Без изменений — вспомогательный сценарий (fn-first-run-setup AC-03), не дублирует таблицу владельца |
| 6 | `lp-bridge-control-by-email.md`, `lp-first-run-setup.md`, `lp-dm-batch-to-email.md`, `lp-channel-update-to-email.md`, `lp-media-in-email.md`, `lp-email-reply-to-tg.md` | НОВЫЕ — по одному профилю нагрузки на функцию с APPLICABLE OE-LOAD, транскрипция из req + кода (интервалы, лимиты, backlog) |
| 7 | `api-mailbox-imap-smtp.md`, `api-telegram-userclient.md` | Business-reject codes (N/A с причиной — реестр пуст); секция обратной ссылки OE-DELIVERY на функции, доставляемые этим API |
| 8 | `context-mailtg-bridge.md` | Секция «Участки доставки (OE-DELIVERY, обратная ссылка)» — все 6 функций |
| 9 | `tc-flt-control-command.md`, `tc-flt-first-run-setup.md`, `tc-flt-inbound-collect-cycle.md`, `tc-flt-outbound-reply.md`, `tc-flt-session-invalid-alert.md` | НОВЫЕ — каталог отказов на каждый сценарий с внешними вызовами (O_T1–O_T6); unavailable+tech-error на каждую точку `scn → api`, взятые из таблиц ошибок `api-*.md` |
| 10 | `tc-int-control-command.md`, `tc-int-inbound-collect-cycle.md`, `tc-int-outbound-reply.md`, `tc-int-session-invalid-alert.md` | `criticality` (была пуста), «## Шаги выполнения» в промышленном step-контракте, ссылки на грани OE и строки `tc-flt/FLT-*` (двусторонние), отдельный лог-шаг для отказных кейсов |
| 11 | `tc-int-first-run-setup.md` | НОВЫЙ — ранее fn-first-run-setup не имел собственного интеграционного теста happy-path (только через вспомогательный session-invalid-alert) |

---

## 8. Критерии приёмки
- AC-1: `check-operational-envelope.py masterspec --scope req` = 0 BLOCKER (было 74). ✓ подтверждено независимым прогоном.
- AC-2: все 6 функций — external_io, 41 грань APPLICABLE + 7 N/A с причиной, 0 OPEN. ✓
- AC-3: Паспорт получил сертификат `meta_model_version: 3.0-req` на первом проходе. ✓ (заменён на
  `3.0-spec` после AC-5/AC-6 — code ещё не мигрирован).
- AC-4: миграция идемпотентна (повторный прогон — no-op). ✓
- AC-5: `check-operational-envelope.py masterspec --scope spec` = 0 BLOCKER (было 125). ✓ подтверждено
  независимым прогоном.
- AC-6: `tc_int_coverage=41/41(100%)`, `fault_tc_coverage=22/22(100%)`, `untested_oe_scenarios=0`. ✓
- AC-7: Паспорт получил сертификат `meta_model_version: 3.0-spec` (scope-квалифицированный — code ещё
  не мигрирован: `--scope code` даёт 41 `untraced in code`, нет `trace-*` в `03-codemap/`). ✓
