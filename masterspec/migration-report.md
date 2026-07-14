---
type: change-artifact
purpose: отчёт прогона masterspec-migrate (форма-переразложение) по фабрике mailtg-bridge
scope_of_run: 14 артефактов (2 api, 2 data, 5 scn, 5 alg) — 02-specifications/{04-apis,05-data,02-scenarios,03-algorithms}
produced_by: migrate
date: 2026-07-13
---

# Migration report — mailtg-bridge (форма-переразложение legacy → schema-first/нотационная)

Прогон `masterspec-migrate` по явному списку 14 артефактов слоя спецификаций. Все 14 — переразложены
(ни один не пропущен как «уже в форме»/«вне scope»/«решение владельца»). Результат — везде
`status: draft` (был `draft` и до прогона — понижать было не с чего, human-gate всё равно обязателен),
`produced_by: migrate` проставлен везде. `boundary` нигде не тронут (вне scope migrate).

## 1. Таблица артефактов

| # | Артефакт | Файлы созданы/изменены | `notation`/`form`/`sidecar_format` | MIGRATE-TODO |
|---|---|---|---|---|
| 1 | api-mailbox-imap-smtp | `api-mailbox-imap-smtp.md` (тонкий компаньон) + `api-mailbox-imap-smtp.asyncapi.yaml` (новый сайдкар) | `sidecar_format: asyncapi-2.x` | 19 (17 типовых полей/версии в сайдкаре + 2 структурных несовпадения request/reply-формы, см. §2) |
| 2 | api-telegram-userclient | `api-telegram-userclient.md` (тело «Операции/Контракт» оставлено as-is — сайдкар НЕ создан) | сайдкар осознанно не заведён (транспорт MTProto RPC без готового стандарта) | 1 |
| 3 | data-bridge-store | `data-bridge-store.md` (тонкий компаньон) + `data-bridge-store.schema.json` (новый сайдкар) | `sidecar_format: json-schema-2020-12` | 14 |
| 4 | data-config | `data-config.md` (тонкий компаньон) + `data-config.schema.json` (новый сайдкар) | `sidecar_format: json-schema-2020-12` | 0 — все типы явно заданы в исходной таблице «Тип» |
| 5 | scn-control-command | frontmatter (`notation`, `produced_by`) | `notation: yaml-graph` | 0 |
| 6 | scn-first-run-setup | frontmatter | `notation: yaml-graph` | 0 |
| 7 | scn-inbound-collect-cycle | frontmatter | `notation: yaml-graph` | 0 |
| 8 | scn-outbound-reply | frontmatter | `notation: yaml-graph` | 0 |
| 9 | scn-session-invalid-alert | frontmatter | `notation: yaml-graph` | 0 |
| 10 | alg-addressing-gate | frontmatter | `form: procedural` | 0 |
| 11 | alg-backoff-on-floodwait | frontmatter | `form: procedural` | 0 |
| 12 | alg-batch-per-dialog-cycle | frontmatter | `form: procedural` | 0 |
| 13 | alg-dedup-idempotency | frontmatter | `form: procedural` | 0 |
| 14 | alg-oversize-degrade | frontmatter | `form: procedural` | 0 |

**Итого MIGRATE-TODO: 34** (19 + 1 + 14 + 0 + 0×5 + 0×5). Все — требуют human-gate владельца перед
`masterspec-verify scope=spec`.

### Как определялась форма (кратко)

- **api-mailbox-imap-smtp**: `Тип API: external-async` (SMTP produce / IMAP consume-поллинг) →
  природа контракта event-driven → `AsyncAPI 2.x` (-> patterns/sidecar-formats.md). Сайдкар создан.
- **api-telegram-userclient**: `Тип API: external-sync`, но транспорт — MTProto RPC поверх
  пользовательской Telethon-сессии. Операции контракта (`list-tracked-dialogs`,
  `fetch-messages-since`, …) — логическая абстракция моста, НЕ имена реальных MTProto/TL-методов;
  готового машинного стандарта под ЭТУ абстракцию нет (TL-схема — про сырой протокол, не про неё;
  OpenAPI/AsyncAPI/protobuf/WSDL/SDL предполагают транспорт, которого тут нет). По фикс-правилу §1 —
  сайдкар НЕ создан, вместо него `MIGRATE-TODO` в компаньоне. Оценка честная: альтернативных
  «спрятанных» стандартов не нашёл, синтезировать не стал.
- **data-bridge-store**: сущности + связи → `JSON Schema 2020-12`, `$defs` на сущность.
- **data-config**: плоская config-схема (таблица «ключ/тип/дефолт», без сущностей/связей) →
  `JSON Schema 2020-12`, свойства прямо в `properties` (-> migration-rules §2 оговорка).
- **5 scn**: во всех — строгая markdown-нумерация «Последовательность шагов» + инлайн-ссылки
  `-> cmp/cap`/`-> api-` на каждом шаге + переходы между сценариями (`-> scn-`) как допустимые узлы.
  Ветвления проверены на полноту (см. методологическую оговорку в §4) — везде оба/все исходы
  условия названы явно (либо парой «X → …; иначе → …», либо N-way перечислением, где N-й исход —
  уже описанный шаг happy-path). Участники нигде не встречаются прозой без slug. → `notation:
  yaml-graph`, БЕЗ holding-route TODO (детекция §9 п.3, не п.4).
- **5 alg**: во всех — «Правила» оформлены пронумерованным прозаическим перечнем (не markdown-таблицей
  «условия→результат») → `form: procedural` (безопасный дефолт, критерий decision-table не выполнен).
  Полнота ветвлений (§10 «если X — иначе Y») проверена — нигде не найдено правило с одним
  неполным исходом. Кандидатов «похоже на классификатор, но не таблица» не оформлял в
  decision-table-TODO: во всех 5 «Правила» — упорядоченные cascades с явно обоснованным порядком
  проверки («Порядок проверок» + «Причины выбора порядка»), т.е. это генуинно процедурная логика
  (short-circuit if/elif), а не одноходовая классификация с независимыми колонками-условиями,
  которую стоило бы то же самое втиснуть в таблицу решений — граница объяснена в §4 ниже.

---

## 2. Полный список MIGRATE-TODO (сквозная нумерация)

Формат: `[артефакт] место — текст TODO — какой факт нужен для закрытия`.

### api-mailbox-imap-smtp (19)

1. **[api-mailbox-imap-smtp]** сайдкар `.asyncapi.yaml:10`, `info.version` — версия контракта не
   зафиксирована в источнике — нужен факт: есть ли у контракта своя версия (или зафиксировать
   «версии нет, контракт = draft», закрыть TODO без цифры).
2. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.from` — тип не указан, legacy: `"from=B
   (обяз.)"` — нужен факт: логический тип (вероятно email-адрес — сверить с `B_ADDRESS: email` в
   data-config.md, но это ДРУГОЙ артефакт, migrate не переносил автоматически).
3. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.to` — тип не указан, legacy: `"to=U (обяз.)"` —
   тот же факт, что #2, для `U_ADDRESS`.
4. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.subject` — тип не указан, legacy: `"subject(с
   тегом источника, обяз.)"` — нужен факт: строка? структура (тег + текст)?
5. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.html_body` — тип не указан, legacy:
   `"html_body(обяз.)"` — нужен факт: строка (HTML) или структура с кодировкой/MIME-метаданными?
6. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.text_body` — тип не указан, legacy:
   `"text_body(обяз.)"` — тот же вопрос, что #5, для текстовой части.
7. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.inline_images[]`, тип элемента — legacy:
   `"inline_images[]"` — нужен факт: форма элемента (ref/bytes/{name,type,size,data}?).
8. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.attachments[]`, тип элемента — legacy:
   `"attachments[]"` — тот же вопрос, что #7, для вложений.
9. **[api-mailbox-imap-smtp]** сайдкар `SendMailInput.notices[]`, тип элемента — legacy: `"notices[]"`
   — нужен факт: форма элемента-уведомления (строка? код+текст?).
10. **[api-mailbox-imap-smtp]** сайдкар `SendMailSuccess.accepted` — тип не указан, legacy: `"успех
    {accepted, message_id (для записи связки)}"` — нужен факт: булево? статус-строка?
11. **[api-mailbox-imap-smtp]** сайдкар `PolledMailItem.from` — тип не указан (поле списка poll-mail)
    — нужен факт: строка-адрес? структура {display_name, address}?
12. **[api-mailbox-imap-smtp]** сайдкар `PolledMailItem.delivered_to` — тип не указан, legacy:
    `"delivered_to(=B?)"` — нужен факт: сам вопросительный знак в источнике («=B?») уже сигнал
    неопределённости у автора спеки, не только у migrate.
13. **[api-mailbox-imap-smtp]** сайдкар `PolledMailItem.references` — тип не указан, legacy:
    `"references?"` — нужен факт: строка (заголовок References целиком) или список Message-ID?
14. **[api-mailbox-imap-smtp]** сайдкар `PolledMailItem.subject` — тип не указан — нужен факт: строка?
15. **[api-mailbox-imap-smtp]** сайдкар `PolledMailItem.text_body` — тип не указан — нужен факт: строка?
16. **[api-mailbox-imap-smtp]** сайдкар `MarkConsumedInput` + компаньон (строка 42) — вход `"uid |
    message_id (обяз.)"` — ровно одно из двух обязательно (XOR), JSON Schema `required` не выражает
    это без `oneOf`; `oneOf`-конструкцию не синтезировал (синтез структуры схемы = домысел) — нужен
    факт: реальный вызывающий код передаёт ОДНО поле или ОБА (одно из них опционально дублирующее)?
17. **[api-mailbox-imap-smtp]** сайдкар `MarkConsumedSuccess.consumed` — тип не указан, legacy: `"успех
    {consumed}"` — нужен факт: булево? timestamp?
18. **[api-mailbox-imap-smtp]** компаньон, строка 45–49 — входные параметры такта poll-mail
    (`mailbox=B`, `consumed_set`) НЕ выражаются в AsyncAPI subscribe-операции (subscribe не имеет
    слота «вход») — нужно решение владельца: завести кастомное расширение (`x-request`?) или принять,
    что эти параметры живут только в компаньоне.
19. **[api-mailbox-imap-smtp]** сайдкар, канал `poll-mail` — то же наблюдение, что #18, отражено в
    `description` канала без формального тега (структурная асимметрия AsyncAPI, не «неизвестный факт»
    в строгом смысле — включено в счёт для полноты, т.к. требует решения владельца).

### api-telegram-userclient (1)

20. **[api-telegram-userclient]** компаньон, раздел «Машинный sidecar» (было: «Не ведётся» → правка
    migrate: «Не создаётся») — стандарт машинной проекции под транспорт MTProto RPC (через Telethon)
    не определён — нужен факт: владелец либо осознанно фиксирует «компаньон без сайдкара» как решение
    по ЭТОМУ API (аналог снятого ранее `.md-only`, но теперь предметно обоснованное), либо указывает
    конкретный стандарт, если он всё же существует и мне не известен.

### data-bridge-store (14) — ✅ ЗАКРЫТО 14.07.2026

**Разрешение:** все 14 (#21–34) закрыты ИЗ ИСТОЧНИКА — `config.py` (Settings) + `-> data-config.schema.json`, без домысла. Типы и построчный провенанс (`from: config.py:NN + data-config.schema.json:NN`) — в `data-bridge-store.schema.json`. Ключевые разрешения: `tg_access` → объект {api_id:int, api_hash:str} (config.py:45); `B_imap/B_smtp` host:str, port:int (config.py:47-48); `credentials` → `$ref MailCredentials`; `whitelist`/`mention_list` элементы → `$ref SourceRef`; `attachment_threshold`/`email_size_limit` → байты, int (config.py:51-52); `collect_interval`/`send_interval` → секунды, int (config.py:52-53); `retention` — НЕ одно поле, а составной ярлык пяти раздельных Settings (config.py:55-57: retention_seconds/max_ledger/max_consumed/max_echo/echo_retention). Детектор формы (F3) на mailtg — зелёный. Ниже — исходный список как аудит того, что было открыто:

21. **[data-bridge-store]** сайдкар `Configuration.tg_access` — тип не указан, legacy: `"tg_access
    (доступ Telegram)"` — нужен факт: что это структурно (флаг доступности? объект с токеном/session
    ref?).
22. **[data-bridge-store]** сайдкар `Configuration.B_imap.host` — тип не указан, legacy: `"B_imap
    {host, port, credentials}"` — нужен факт: строка-хост (согласуется с `data-config.B_IMAP_HOST:
    строка`, но НЕ перенесено автоматически — другой артефакт).
23. **[data-bridge-store]** сайдкар `Configuration.B_imap.port` — тип не указан — нужен факт: целое
    (согласуется с `data-config.B_IMAP_PORT: целое, >0`, не перенесено автоматически).
24. **[data-bridge-store]** сайдкар `Configuration.B_imap.credentials` — тип не указан — нужен факт:
    структура (username+password? согласуется с `B_USERNAME`/`B_PASSWORD` в data-config, не перенесено
    автоматически).
25. **[data-bridge-store]** сайдкар `Configuration.B_smtp.host` — тип не указан — тот же вопрос, что
    #22, для SMTP.
26. **[data-bridge-store]** сайдкар `Configuration.B_smtp.port` — тип не указан — тот же вопрос, что
    #23, для SMTP.
27. **[data-bridge-store]** сайдкар `Configuration.B_smtp.credentials` — тип не указан — тот же
    вопрос, что #24, для SMTP.
28. **[data-bridge-store]** сайдкар `Configuration.whitelist[]`, тип элемента — legacy: `"whitelist
    (набор источников)"` — нужен факт: строка-источник в каком формате (согласуется с
    `canonical_source` из data-config, не перенесено автоматически).
29. **[data-bridge-store]** сайдкар `Configuration.mention_list[]`, тип элемента — тот же вопрос, что
    #28.
30. **[data-bridge-store]** сайдкар `Configuration.attachment_threshold` — тип/точность не указаны,
    legacy: `"attachment_threshold (размер)"` — нужен факт: целое число байт? (аналогия с «сумма» из
    migration-rules §3 — точность не очевидна из слова «размер»).
31. **[data-bridge-store]** сайдкар `Configuration.email_size_limit` — тот же вопрос, что #30.
32. **[data-bridge-store]** сайдкар `Configuration.retention` — legacy: `"retention
    (длительность/лимит)"` — составное значение (ДВА разных смысла в одном слове — длительность ИЛИ
    лимит-количество) — нужен факт: это одно поле или должно быть два разных атрибута?
33. **[data-bridge-store]** сайдкар `Configuration.collect_interval` — legacy: `"collect_interval
    (длительность)"` — «длительность» отсутствует в таблице конвертации логических типов
    (migration-rules §3) — нужен факт: секунды (целое)? ISO-8601 duration (строка)?
34. **[data-bridge-store]** сайдкар `Configuration.send_interval` — тот же вопрос, что #33.

### data-config (0)

Все параметры имеют явный `Тип` в собственной таблице источника (целое/строка/email/перечисление/
JSON-массив/булево/путь) — конвертация в JSON Schema прошла без единого пробела. Единственное
пограничное решение без TODO: `email` смаппирован в `type: string, format: email` (формат `email` не
входит в буквальный список migration-rules §3, но это прямая транскрипция ЯВНО заявленного в
источнике типа, не домысел — см. §4).

### 5 scn + 5 alg (0)

Ни одного структурного MIGRATE-TODO — обоснование см. §1 «Как определялась форма» и методологическую
оговорку в §4.

---

## 3. Валидность сайдкаров

Проверено `python3` (`yaml.safe_load` / `json.load`) — все три сайдкара парсятся без ошибок, без
markdown-ограждений внутри:

| Файл | Проверка | Результат |
|---|---|---|
| `api-mailbox-imap-smtp.asyncapi.yaml` | `yaml.safe_load` | OK (top-level: asyncapi, info, channels, components) |
| `data-bridge-store.schema.json` | `json.load` | OK (8 `$defs`) |
| `data-config.schema.json` | `json.load` | OK (40 properties) |

Фронтматтер всех 14 `.md` также провалидирован `yaml.safe_load` — парсится без ошибок, ожидаемые
ключи (`sidecar_format`/`sidecar`/`notation`/`form`/`produced_by`) на месте, `boundary` нигде не
появился.

---

## 4. Где вычищенный скилл всё ещё неясен / потребовал самостоятельного суждения

- **Критерий «полное ветвление» (§9 п.3 vs п.4) не различает N-way категоризацию от бинарного
  if/else.** Буквальный текст правила («если X — A, иначе — B» БЕЗ «иначе» → holding route) написан
  под БИНАРНЫЙ случай. У всех 5 scn этой фабрики нередко встречается паттерн: «Ветвления» называют
  ТОЛЬКО отклонения от happy-path (например, scn-control-command п.4–5: «ответ» и
  «нераспознанная команда» названы явно, а «это команда вкл/выкл» — НЕ повторяется отдельной строкой,
  потому что это и есть уже описанный шаг 4 «Последовательность шагов»). Я трактовал такой
  N-way-паттерн как ПОЛНЫЙ (все исходы названы — просто «главный» исход не дублируется, он уже есть в
  шагах), а не как «одна ветка не описана». Это осознанное решение, НЕ буквальная процедура из
  migration-rules.md — если трактовать правило дословно/буквально (только явное слово «иначе» рядом с
  каждым «если»), часть этих же 5 сценариев (и, вероятно, большинство «зрелых» спек в принципе)
  пришлось бы отправить в holding route почти механически, что противоречит собственной формулировке
  §9 «строгая нумерация + полные ветвления — ОСНОВНОЙ практический случай» (не редкий). Владельцу
  стоит явно решить, какая трактовка канонична, и, если нужно, зафиксировать её в migration-rules.md
  примером (текущий пример §9 показывает только чистый бинарный случай, а N-way с «умолчание = happy
  path» — нет).
- **Критерий «кандидат в decision-table» (§10) не даёт операционного теста «cascade vs таблица».**
  Все 5 alg этой фабрики — упорядоченные if/elif-cascade с явным разделом «Причины выбора порядка»,
  что я счёл достаточным основанием для «это процедурная логика, а не таблица», но правило прямо не
  говорит, что «есть явное обоснование порядка» снимает подозрение «похоже на классификатор». Если
  трактовать иначе, минимум alg-backoff-on-floodwait (3 непересекающихся класса ошибки → 3 реакции)
  можно было бы пометить TODO «кандидат в decision-table». Пограничный случай, решил в пользу
  procedural + без TODO, но стоит сверить с владельцем при human-gate.
- **AsyncAPI не имеет нативного слота «вход» для `subscribe`-операции** (poll-mail: `mailbox=B`,
  `consumed_set`) и не имеет нативного слота «ответ» отдельно от «сообщение» (send-mail/mark-consumed
  success/failure). Это не пробел контента, а структурное несовпадение request/reply-формы исходного
  API с fire-and-forget-формой AsyncAPI — `patterns/sidecar-formats.md` не даёт указания, как поступать
  (пометить в description? завести `x-`-расширение? разбить на два разных канала «запрос»/«ответ»?).
  Решил не изобретать расширение самостоятельно и пометить как MIGRATE-TODO к владельцу (#16, #18–19).
- **`sidecar_format` для email-формата в data-config** — использовал `format: email` в JSON Schema,
  хотя буквальной строки «email» нет в таблице логических типов migration-rules §3 (там только
  URI/URL/UUID/date-time и т.д.). Транскрибировал напрямую из явно заявленного в источнике типа
  (`| B_ADDRESS | email | ...`), решил, что это не домысел, а перенос as-is — но правило не покрывает
  этот случай явно, стоит явно зарегистрировать «email» как формат в таблице §3.
- **§2 «Плоская data без ER-сущностей»** сформулирован коротко (одна оговорка), но не даёт примера
  готовой сконвертированной config-схемы — я ориентировался на неё по аналогии с обычной
  data-schema-конвертацией плюс здравым смыслом «свойства прямо в properties»; результат (40
  properties, 0 TODO) получился настолько гладким, что стоит сверить с владельцем, не пропустил ли я
  тонкость, специфичную для config-паттерна (например, обязательность envvar vs JSON Schema
  `required` — это разные семантики: envvar отсутствует/пуст ⇒ ошибка старта, а JSON Schema `required`
  формально проверяет только «ключ присутствует в объекте», что не то же самое, что «переменная
  окружения задана» — граница между «конфиг как JSON-документ» и «конфиг как env» этим сайдкаром явно
  не прописана, хотя и не показалась мне отдельным TODO, т.к. форма самого JSON Schema тут вторична
  относительно факта типов).

---

## 5. Не тронуто (вне scope migrate)

- `boundary` — ни в одном из 2 api не проставлен (ни значением, ни TODO) — Фаза 5, не эта задача.
- OE-таблицы «Реализация контракта живой эксплуатации» в scn — не проверялись на полноту (не migrate).
- Кросс-артефактные нестыковки, замеченные по ходу (например, `data-bridge-store.md`
  `Конфигурация.B_address` в маппинге `api-mailbox-imap-smtp` не имеет прямого одноимённого атрибута
  в самой сущности `Конфигурация` data-bridge-store — там нет отдельного `B_address`, только
  `B_imap`/`B_smtp`-объекты) — НЕ исправлялись: это предмет `verify` (O2/O6), не формы.

---

## 6. Закрытие R-TODO из источника

Прогон второй фазы (branch `feat/spec-schema-first-migrate`): 30 TODO класса R (§2 №2–17, №21–34)
закрыты типом/структурой ТОЛЬКО там, где факт нашёлся в источнике истины (data-config,
`src/mailtg_bridge/*.py`, RFC 5322) — без домысла. Где факта нет, TODO оставлен и явно помечен
«остаётся O» с объяснением, какого факта не хватает. `boundary`, №1/№18–20 не тронуты (вне scope).

### api-mailbox-imap-smtp.asyncapi.yaml (16: №2–17)

| № | Поле | Результат |
|---|---|---|
| 2 | `SendMailInput.from` | **ЗАКРЫТ: `string, format: email`** from data-config.schema.json:16 (B_ADDRESS) + config.py:46 (`b_address`, `_email()`) |
| 3 | `SendMailInput.to` | **ЗАКРЫТ: `string, format: email`** from data-config.schema.json:21 (U_ADDRESS) + config.py:49 (`u_address`, `_email()`) |
| 4 | `SendMailInput.subject` | **ЗАКРЫТ: `string`** from mail_out.py:71 (`msg["Subject"]=base+...`), :131 (`send_notice(subject: str)`) |
| 5 | `SendMailInput.html_body` | **ЗАКРЫТ: `string`** from mail_out.py:65 (`markup="<html><body>..."`), :72 (`add_alternative(markup, subtype="html")`) |
| 6 | `SendMailInput.text_body` | **ЗАКРЫТ: `string`** from mail_out.py:65 (`plain="\n\n".join(plain)`), :72 (`msg.set_content(...)`) |
| 7 | `SendMailInput.inline_images[]` | **ЗАКРЫТ: object `MediaAttachment` {filename, content_type, size}** from domain.py:62–66 (`MediaRef`) + mail_out.py:60–63,77–79 (image branch → `add_related`); disposition `inline-image` -> dict-media-disposition |
| 8 | `SendMailInput.attachments[]` | **ЗАКРЫТ: object `MediaAttachment`** (тот же тип, что №7) from mail_out.py:58–59,80 (`elif dm.size<=threshold: msg.add_attachment`); disposition `attached-file` -> dict-media-disposition |
| 9 | `SendMailInput.notices[]` | **ОСТАЛСЯ O (не выводимо):** в реальном коде нет коллекции "notices" внутри ОДНОГО `SendMailInput` — (а) BridgeService-уведомления идут отдельными вызовами `send_notice(subject,body)`, по одному письму на уведомление (mail_out.py:130–132, orchestrator.py:102–107), не элементом массива; (б) markers "notice-only" (-> dict-media-disposition) вписаны строками прямо в `html_body`/`text_body` (mail_out.py:58–59), не собираются в отдельный массив. Ни одно чтение не даёт структуры элемента |
| 10 | `SendMailSuccess.accepted` | **ОСТАЛСЯ O (не выводимо):** `SmtpMailer.send()` (mail_out.py:100–113) не перехватывает и не сохраняет результат `smtp.sendmail()` (dict отклонённых адресатов отбрасывается); успех выражен только отсутствием исключения — ни поля, ни переменной "accepted" в коде нет |
| 11 | `PolledMailItem.from` | **ЗАКРЫТ: `string`** from domain.py:117 (`InboundMail.from_addr: str`) + mail_in.py:95 (`parseaddr(...)[1].lower()`) |
| 12 | `PolledMailItem.delivered_to` | **ЗАКРЫТ: `array<string>`** from domain.py:118 (`InboundMail.recipients: tuple[str,...]`) + mail_in.py:92–93 (объединение To/Delivered-To/X-Original-To) |
| 13 | `PolledMailItem.references` | **ЗАКРЫТ: `array<string>`** (список Message-ID, -> RFC 5322 References) from domain.py:123 (`references: tuple[str,...]`) + mail_in.py:17–18,96 (`message_ids()`) |
| 14 | `PolledMailItem.subject` | **ЗАКРЫТ: `string`** from domain.py:119 (`InboundMail.subject: str`) + mail_in.py:95 (`decode_header_value`) |
| 15 | `PolledMailItem.text_body` | **ЗАКРЫТ: `string`** from domain.py:120 (`InboundMail.body_text: str`) + mail_in.py:79–84,96 (`extract_reply_text()`) |
| 16 | `MarkConsumedInput` uid⊕message_id | **ЗАКРЫТ: `required: [uid]`** — реальный вызывающий код (orchestrator.py:79,87,97) ВСЕГДА передаёт ровно `mail_ref` (IMAP UID-строка, mail_in.py:124) под ключом `uid`; `message_id` нигде не используется как ключ потребления (grep src/+tests/ — 0 вызовов) → факт закрывает XOR без синтеза `oneOf` |
| 17 | `MarkConsumedSuccess.consumed` | **ОСТАЛСЯ O (не выводимо):** `mark_consumed(ref)` (state.py:118–119) возвращает `None`; ни один вызывающий код не строит результат-объект с полем "consumed" |

### data-bridge-store.schema.json (14: №21–34)

| № | Поле | Результат |
|---|---|---|
| 21 | `Configuration.tg_access` | **ЗАКРЫТ: object {api_id: integer, api_hash: string}** from config.py:45 (`tg_api_id: int; tg_api_hash: str`) + data-config.schema.json:13–14 (TG_API_ID/TG_API_HASH); `session_path` — уже отдельное соседнее поле, не входит сюда |
| 22 | `Configuration.B_imap.host` | **ЗАКРЫТ: `string`** from config.py:47 (`b_imap_host: str`) + data-config.schema.json:19 (B_IMAP_HOST) |
| 23 | `Configuration.B_imap.port` | **ЗАКРЫТ: `integer`** from config.py:47 (`b_imap_port: int`, >0) + data-config.schema.json:26 (B_IMAP_PORT, default 993) |
| 24 | `Configuration.B_imap.credentials` | **ЗАКРЫТ: `$ref MailCredentials` {username, password: string}** from config.py:46 (`b_username`/`b_password`) + mail_in.py:113 (`ImapMailbox._connect` login) |
| 25 | `Configuration.B_smtp.host` | **ЗАКРЫТ: `string`** from config.py:48 (`b_smtp_host: str`) + data-config.schema.json:20 (B_SMTP_HOST) |
| 26 | `Configuration.B_smtp.port` | **ЗАКРЫТ: `integer`** from config.py:48 (`b_smtp_port: int`, >0) + data-config.schema.json:27 (B_SMTP_PORT, default 465) |
| 27 | `Configuration.B_smtp.credentials` | **ЗАКРЫТ: `$ref MailCredentials`** (та же пара, что №24 — общий логин/пароль ящика B) from mail_out.py:106,125 (`SmtpMailer` login) |
| 28 | `Configuration.whitelist[]` | **ЗАКРЫТ: `$ref SourceRef` (string, canonical_source)** from config.py:37–41 (`canonical_source()`) + config.py:49 (`whitelist: tuple[str,...]`) |
| 29 | `Configuration.mention_list[]` | **ЗАКРЫТ: `$ref SourceRef`** (тот же тип, что №28) from config.py:50 (`mention_list: tuple[str,...]`) |
| 30 | `Configuration.attachment_threshold` | **ЗАКРЫТ: `integer` (байты)** from config.py:51 (`attachment_threshold_bytes: int`, default `10*1024*1024`) + data-config.schema.json:58 (ATTACHMENT_THRESHOLD_BYTES, default 10485760) |
| 31 | `Configuration.email_size_limit` | **ЗАКРЫТ: `integer` (байты)** from config.py:52 (`email_size_limit_bytes: int`, default `24*1024*1024`) + data-config.schema.json:59 (EMAIL_SIZE_LIMIT_BYTES, default 25165824) |
| 32 | `Configuration.retention` | **ЗАКРЫТ: object с 5 полями** `retention_seconds`/`retention_max_ledger`/`retention_max_consumed`/`retention_max_echo`/`echo_retention_seconds` (все `integer`) — legacy-ярлык «retention» в реальном коде оказался пятью раздельными полями `Settings`, не одним значением; from config.py:55–57 + data-config.schema.json:63–67 |
| 33 | `Configuration.collect_interval` | **ЗАКРЫТ: `integer` (секунды)** from config.py:52 (`collect_interval_seconds: int`, default 60) + data-config.schema.json:55 |
| 34 | `Configuration.send_interval` | **ЗАКРЫТ: `integer` (секунды)** from config.py:53 (`send_interval_seconds: int`, default 30) + data-config.schema.json:56 |

### Итог

**Закрыто: 27 / 30** (api-mailbox-imap-smtp: 13 из 16 — №2–8, №11–16; data-bridge-store: 14 из 14 — №21–34).
**Осталось O (не выводимо): 3** — №9 (`notices[]`: такой коллекции внутри одного `SendMailInput` в реальном
коде нет), №10 (`accepted`: код нигде не строит это значение, только отсутствие исключения) и №17
(`consumed`: `mark_consumed()` возвращает `None`, поля-результата нет). Все три требуют, чтобы владелец либо
предъявил недостающий факт в реальном коде (которого сейчас там нет), либо решил оставить поле
неопределённым/убрать из контракта.

Побочная находка (не TODO, вне scope этой правки — только к сведению владельца): `PolledMailItem.in_reply_to`
и `SendMailInput.in_reply_to` уже были типизированы как `string` ДО этого прогона (не помечены MIGRATE-TODO),
но `domain.py:122` (`InboundMail.in_reply_to: tuple[str,...]`) и `mail_in.py:96` показывают, что фактически
это массив Message-ID (как и `references`) — не единственная строка. Не исправлено намеренно: не входит в
список 30 R-TODO, правка типа непомеченного поля — предмет `verify`, не этой задачи.

Валидность после правки: `python3 -c "import yaml; yaml.safe_load(open('api-mailbox-imap-smtp.asyncapi.yaml'))"`
и `python3 -c "import json; json.load(open('data-bridge-store.schema.json'))"` — оба сайдкара парсятся;
дополнительно оба JSON Schema (`data-bridge-store.schema.json`, `data-config.schema.json`) прошли
`jsonschema.validators.Draft202012Validator.check_schema()` без ошибок.
