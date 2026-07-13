# Apply-report: oe-migration-3.0 (боевой apply-change, migration-класс)

**Change:** oe-migration-3.0 · **Factory:** mailtg-bridge · **Дата:** 2026-07-13

## Применено (MIGRATED, in-place, draft direct-to-tree)
- 6 функций `01-requirements/02-functions/fn-*.md` — добавлены `criticality`, `Внешний инициатор/канал`, секция OE (8 граней).
- 7 `01-requirements/08-test-cases/tc-acc-*.md` — добавлены `criticality`, «Грани:» (трассы `-> fn/OE-*`), step-contract.
- `status` сохранён `draft` (migration-класс не форсит actual — `merge-workflow.md §5.5`).

## Verification (независимый прогон детектора)
```
OE metrics: functions=6 external_io=6 internal_only=0 expected_facets=48 applicable=41
n_a_with_reason=7 open=0 tc_acc_coverage=41/41(100.00%) tc_acc_weighted=151/151(100.00%)
```
BLOCKER req: 0 (было 74) · exit 0.

## Сертификация версии
- Прогон детекторов по scope: **req = OK (0 BLOCKER)**; spec = 125 BLOCKER; code = 166 BLOCKER.
- Итог: scope-квалифицированный сертификат **`meta_model_version: 3.0-req`** в Паспорте (req-слой соответствует 3.0; spec/code — следующий шаг миграции, `scn-`/`api-`/`lp-`/`trace-` без OE-таблиц).
- Полный `3.0` (без квалификатора) откроется, когда OE протрассируется в spec/code.

## Идемпотентность (req)
Повторный прогон детектора после штампа — 0 BLOCKER; повторная сертификация — no-op (штамп уже `3.0-req`).

---

# Продолжение: спецификации (`--scope spec`)

## Контур (references/migration.md)
1. **Детекция.** `check-operational-envelope.py masterspec --scope spec` на состоянии после req-прохода
   → 125 BLOCKER: `unrealized in scn` (41 — OE-грани не протрассированы в `scn-`), `OE-LOAD has no lp`
   (6), `OE-DELIVERY has no external api` (6), `OE-DELIVERY has no context path` (6), 4× `tc-int-*` без
   `criticality`/`Шаги выполнения`/лог-шага, `uncovered by tc-int via scn` (41), 5× `scenario … with api
   calls has 0 fault catalogs`.
2. **Дозаполнение.** По каждой дыре — транскрипция из уже готового req-слоя (fn-*/OE-* граней) и кода:
   - 4 `scn-*.md` (control-command, first-run-setup, inbound-collect-cycle, outbound-reply) получили
     секцию «Реализация контракта живой эксплуатации» — union граней покрывает все 41 APPLICABLE;
     `scn-session-invalid-alert.md` НЕ получил таблицу (вспомогательный, во избежание дублирования
     владения single-source).
   - 6 новых `lp-*.md` (по функции с APPLICABLE OE-LOAD) — интервалы/лимиты/backlog из fn-*/OE-LOAD +
     кода (`config.py`).
   - `api-mailbox-imap-smtp.md` / `api-telegram-userclient.md` — Business-reject codes (N/A, реестр
     пуст — вся таксономия исчерпана транспортной таблицей) + обратная ссылка OE-DELIVERY.
   - `context-mailtg-bridge.md` — обратная ссылка OE-DELIVERY на все 6 функций (участки доставки).
   - 5 новых `tc-flt-*.md` (по сценарию с внешними вызовами) — unavailable+tech-error на каждую точку
     `scn → api`, взятые из таблиц ошибок `api-*.md`; business-reject N/A (реестр пуст).
   - 4 `tc-int-*.md` дополнены `criticality` (не ниже функции), промышленным step-контрактом («## Шаги
     выполнения»), ссылками на грани OE и двусторонними ссылками на `tc-flt/FLT-*`, отдельным лог-шагом
     для отказных путей. 1 новый `tc-int-first-run-setup.md` — ранее happy-path авторизации не имел
     отдельного интеграционного теста (только через вспомогательный session-invalid-alert).
3. **Перепрогон.** Итерация 1 → 24 BLOCKER (все структурные дыры сняты, остались только
   `tc-int-*`-дефекты). Итерация 2 (правки tc-int) → 12 BLOCKER: две fault-catalog ошибочно ссылались
   на ВТОРОЙ сценарий (`scn-session-invalid-alert`) внутри текста результата FLT-строки, что ломало
   «catalog references exactly one scenario» и резолвинг шагов (O_T4). Правка — убрать `->`-ссылку,
   оставить прозу. Итерация 3 → 0 BLOCKER.
4. **Сертификация.** Штамп `meta_model_version: 3.0-spec` (req+spec пройдены; code — untraced, 41
   `fn-*/OE-*` без `trace-*`, следующий шаг миграции).

## Verification (независимый прогон детектора, --scope spec)
```
OE metrics: functions=6 external_io=6 internal_only=0 expected_facets=48 applicable=41
n_a_with_reason=7 open=0 tc_acc_coverage=41/41(100.00%) tc_acc_weighted=151/151(100.00%)
uncovered_by_tc=0 unrealized_in_spec=0 uncovered_by_tc_int=0
tc_int_coverage=41/41(100.00%) tc_int_weighted=151/151(100.00%)
fault_tc_coverage=22/22(100.00%) untested_oe_scenarios=0 untraced_in_code=41
```
BLOCKER spec: 0 (было 125) · exit 0. `--scope req` перепроверен тем же прогоном: 0 BLOCKER, без
регресса.

## Идемпотентность (spec)
Повторный прогон детектора после штампа — 0 BLOCKER на `--scope req` и `--scope spec`; повторная
сертификация — no-op (штамп уже `3.0-spec`).

## Остаток (честно не закрыто)
`--scope code` — 41 `untraced in code` (нет `trace-*` в `03-codemap/02-scenario-traces/`): код-слой
следующий шаг этой же миграции, полный `3.0` (без квалификатора) откроется тогда.

## Откат
`git checkout HEAD -- masterspec/01-requirements/02-functions/ masterspec/01-requirements/08-test-cases/ masterspec/01-requirements/01-system/ masterspec/02-specifications/02-scenarios/ masterspec/02-specifications/07-load-profiles/ masterspec/02-specifications/04-apis/external/ masterspec/01-requirements/05-landscape/context-mailtg-bridge.md`
(для 08-test-cases — откатить только `tc-int-*`/`tc-flt-*` под `02-specifications/`, не затрагивая req-слой).
