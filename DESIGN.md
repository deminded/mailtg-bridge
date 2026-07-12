# Имплементационный дизайн `mailtg-bridge`

Статус: design-gate, код не реализован. Язык реализации — Python 3.11+. Документ проектирует v1 по `masterspec`; при расхождении приоритет имеют спецификации и принятые verify-ответы.

## 1. Границы и архитектурный стиль

Мост — один headless-процесс с двумя независимыми расписаниями внутри общего `asyncio`-цикла: Telegram → email (`collect_interval`) и IMAP → Telegram/команды (`send_interval`). Экземпляр на всё время жизни удерживает неблокирующий эксклюзивный `flock`; второй экземпляр сразу завершается с отдельным кодом. Такты исполняются последовательно и не разделяют Telethon-сессию конкурентно.

Архитектура — application services + порты/адаптеры. Оркестратор знает только протоколы Telegram, почты и хранилища. MIME, Telethon, IMAP/SMTP и SQLite изолированы в адаптерах. Это сохраняет провайдер-нейтральность и делает алгоритмы тестируемыми без сети.

В v1 персистентное состояние хранится в SQLite вне репозитория. Причины: уникальные ключи, монотонный cursor, атомарные `ledger → cursor` изменения и bounded-retention надежнее реализуются транзакциями, чем несколькими JSON-файлами. Сам факт SMTP-отправки не входит в транзакцию, поэтому гарантия остаётся at-least-once: дубль допустим, потеря — нет.

## 2. Структура проекта

```text
mailtg-bridge/
├── pyproject.toml
├── README.md
├── .env.example                 # только несекретные примеры/плейсхолдеры
├── src/mailtg_bridge/
│   ├── __init__.py
│   ├── __main__.py              # CLI: run, setup, check-config, once, purge
│   ├── config.py                # Settings, enum/pарсинг/валидация .env
│   ├── domain.py                # dataclass/enum: Dialog, TgMessage, Batch, MailDraft…
│   ├── errors.py                # FloodWait, Transient, SessionInvalid, ConfigError…
│   ├── ports.py                 # Protocol-интерфейсы TgGateway/MailIn/MailOut/Store/Clock
│   ├── orchestrator.py          # BridgeService, расписание и application flows
│   ├── algorithms.py            # чистые addressing/batching/backoff/oversize/deeplink
│   ├── state.py                 # StateStore API и SQLiteStore
│   ├── telegram.py              # TelethonGateway + интерактивная авторизация
│   ├── mail_in.py               # IMAP poll, MIME parse, trust/classification
│   ├── mail_out.py              # MIME compose, HTML/text/media, SMTP send
│   ├── commands.py              # строгий парсер token-команд on/off
│   ├── locking.py               # lifetime flock
│   ├── logging.py               # structured metadata, redaction
│   └── setup.py                 # setup flow, chmod/session-health
├── deploy/
│   ├── mailtg-bridge.service
│   └── mailtg-bridge.env.example
└── tests/
    ├── unit/                    # чистые алгоритмы, parser, MIME, store invariants
    ├── integration/             # SQLite + fake ports; каждый scn-* как flow
    └── contract/                # fake IMAP/SMTP и Telethon mapping/smoke
```

`domain.py` содержит неизменяемые модели: `SourceType(dm|channel|group|topic)`, `MentionPolicy(all|selected|forced_list)`, `DialogRef`, `Cursor`, `Sender`, `MessageEntity`, `MediaRef`, `DownloadedMedia`, `TgMessage`, `DialogBatch`, `RenderedMessage`, `MailDraft`, `SentMail`, `InboundMail`, `MailKind(reply|command|ignore)`, `BridgeState`, `SessionHealth`, `BackoffDecision`. Байты медиа живут только в рамках такта/временного каталога и не попадают в состояние или логи.

## 3. Маппинг спецификации на код

### 3.1. Компоненты

| Спека | Реализация | Основные методы/capabilities |
|---|---|---|
| `cmp-bridge-orchestrator` | `orchestrator.BridgeService` | `run()`, `run_inbound_cycle()`, `run_mailbox_cycle()`, `delivery_allowed()`, `assemble_batch()`, `record_failure()` |
| `cmp-tg-gateway` | `telegram.TelethonGateway` | `list_tracked_dialogs()`, `fetch_since()`, `is_bridge_echo()`, `download_media()`, `post_as_user()`, `classify_error()`, `authorize_interactive()` |
| `cmp-email-out` | `mail_out.EmailComposer`, `mail_out.SmtpMailer` | `compose_batch()`, `build_deeplink()`, `render_media()`, `degrade()`, `send()`, `send_notice()` |
| `cmp-email-in` | `mail_in.ImapMailbox`, `mail_in.MailClassifier` | `poll()`, `authenticate()`, `classify()`, `resolve_parent_ids()`, `extract_reply_text()`; consume marker пишет Store после действия |
| `cmp-state-store` | `state.SQLiteStore`, `config.Settings` | cursor/ledger/consume/echo/bridge/session CRUD, `commit_delivery()`, `purge_retention()`; конфигурация read-only |

`cap-mark-consumed` логически принадлежит email-in, но физическая запись выполняется через `SQLiteStore.mark_consumed()` — после успешного Telegram post или полного исполнения команды и подтверждения согласно выбранной семантике из открытого вопроса Q2.

### 3.2. Сценарии как application flows

| Сценарий | Поток реализации |
|---|---|
| `scn-inbound-collect-cycle` | `BridgeService.run_inbound_cycle`: gates → dialogs/cursors → fetch → cursor/echo/addressing filters → batch → media → MIME/degrade → SMTP → ledger → cursor |
| `scn-outbound-reply` | `BridgeService.handle_reply`: consumed check → trust → ledger resolve → bridge/session gate → post → echo marker → consume marker |
| `scn-control-command` | `BridgeService.handle_command`: consumed check → trust + parent-ledger + token → parse → persistent toggle → confirmation → consume marker |
| `scn-first-run-setup` | CLI `setup` → `setup.run_setup`: Telethon phone/code/2FA → verify `get_me()` → chmod 600 → session valid, `notified=false` |
| `scn-session-invalid-alert` | `BridgeService.invalidate_session`: atomic valid=false/notified=false → stop all Telegram calls → SMTP notice → on success notified=true; retry notice only on later scheduled wake-up |

Команды опрашиваются даже при `bridge.enabled=false`, иначе email-командой мост нельзя включить. Ответы и оба направления доставки требуют `enabled && session.valid`. При invalid session IMAP может опрашиваться только для команд и попытки неотправленного session notice; Telegram не вызывается.

### 3.3. Алгоритмы

| Спека | Функции/объекты |
|---|---|
| `alg-addressing-gate` | `algorithms.is_addressed(message, dialog, whitelist, policy, mention_list) -> bool` |
| `alg-batch-per-dialog-cycle` | `algorithms.make_dialog_batch(...)`, `SQLiteStore.commit_delivery(...)` |
| `alg-dedup-idempotency` | `msg_id > cursor`, `SQLiteStore.is_consumed/mark_consumed`, echo table, ledger lookup |
| `alg-backoff-on-floodwait` | `algorithms.next_backoff(error, failures, minimum, maximum, now)` + per-operation `RetryState` |
| `alg-oversize-degrade` | `EmailComposer.plan_parts(batch, limits)` и точная `len(message.as_bytes(policy=SMTP))` |

### 3.4. Внешние API

`api-telegram-userclient` реализует `TelethonGateway`. Он нормализует Telethon-объекты в доменные модели и переводит исключения в `FloodWait(wait_seconds)`, `SessionInvalid`, `Transient`, `PeerNotFound`, `MediaUnavailable`. Любая auth/session ошибка на list/fetch/download/post консервативно инвалидирует общую session-health.

`api-mailbox-imap-smtp` разделён на `ImapMailbox` и `SmtpMailer`. TLS обязателен; host/port/security берутся из конфигурации. Адаптер переводит сеть/таймаут/4xx/rate-limit в `Transient`, auth — в терминальный `MailAuthError`, отказ по размеру — в `MailSizeRejected`. `poll()` использует IMAP UID как transport cursor, но бизнес-идемпотентность определяется persisted `mail_ref = mailbox-id + UIDVALIDITY + UID` (с fallback на нормализованный Message-ID), а не флагом `Seen`.

### 3.5. Данные

`data-bridge-store` реализуется связкой `config.Settings` (read-only deployment config) и `state.SQLiteStore` (mutable state). Cursor, ledger, consume marker, echo marker и оба singleton-state имеют прямые таблицы; ограничения уникальности, монотонности и retention обеспечиваются Store API и SQL constraints/transactions. Физическая схема и crash semantics приведены в разделе 5.

## 4. Переиспользование обкатанного ядра

Переиспользование означает перенос с сохранением поведения и тестовое закрепление, а не импорт исполняемых соседних скриптов по абсолютному пути.

Из `/home/claude-user/channel-reader/reader.py` берём паттерн одного `TelegramClient`, `iter_messages(entity, min_id=cursor, limit=...)`, разворот результата в хронологический порядок и per-dialog cursor. Адаптируем: первый запуск не «тихий хвост», а определяется явной bootstrap-политикой; cursor хранится в SQLite; high-watermark — `max(msg.id)` всех выбранных сообщений, включая echo/gated-out; пустые/медиа-only сообщения не отбрасываются до гейта.

Из `/home/claude-user/de-agent-commons/src/agentcommons/email.py` переиспользуем/выделяем `read_creds`-подобный env parsing, TLS IMAP/SMTP, `BODY.PEEK[]`, RFC2047 decoding, адресную нормализацию `is_allowed`, anti-auto-loop `is_auto_or_loop`, Message-ID/References parsing и атомарную идею `MessageLedger`. `send_email` расширяем до `EmailMessage` с `multipart/alternative`, `multipart/related`, CID inline images, attachments, настраиваемыми портами и SSL/STARTTLS. `MessageLedger` не используем как отдельный JSON: его проверенный контракт `record_sent/is_our_thread` переносится в SQLite ledger с `dialog_id` и retention.

Из `/home/claude-user/email_poller.py` берём последовательный IMAP high-watermark/неперешагивание сбоя, нормализацию заголовков против CRLF, allowlist-проверку и действие-before-consume. Не переносим Telegram-bot уведомления, queue/outbox и адреса: они не входят в этот мост.

Из `/home/claude-user/arete-userbot/` берём создание `TelegramClient(session, api_id, api_hash)`, `get_messages`/`send_message`, `download_media`, двухфазную phone-code авторизацию и обработку `SessionPasswordNeededError`, после чего chmod 600. Новое: типизированный gateway, единая классификация ошибок, list dialogs/topics, entities/mentions/replies/deep-link metadata и session-health.

Новыми остаются оркестратор обоих направлений, SQLite state store, addressing/oversize algorithms, HTML renderer, token-command parser, lifecycle flock, retention и session-invalid flow.

## 5. Персистентность и атомарность

SQLite открывается с foreign keys, WAL, `busy_timeout`, `synchronous=FULL`; файл и каталог создаются с mode 600/700. Миграции имеют `schema_version` и выполняются до сетевых подключений.

```sql
dialog_cursor(dialog_id TEXT PRIMARY KEY, source_type TEXT, last_id INTEGER CHECK(last_id>=0),
              whitelisted INTEGER, source_tag TEXT, updated_at TEXT)
mail_ledger(message_id TEXT PRIMARY KEY, dialog_id TEXT NOT NULL, source_type TEXT,
            sender TEXT, delivered_at TEXT, FOREIGN KEY(dialog_id) REFERENCES dialog_cursor)
consumed_mail(mail_ref TEXT PRIMARY KEY, consumed_at TEXT)
posted_echo(dialog_id TEXT, posted_msg_id INTEGER, posted_at TEXT,
            PRIMARY KEY(dialog_id, posted_msg_id))
bridge_state(singleton INTEGER PRIMARY KEY CHECK(singleton=1), enabled INTEGER, updated_at TEXT)
session_health(singleton INTEGER PRIMARY KEY CHECK(singleton=1), valid INTEGER, notified INTEGER, updated_at TEXT)
runtime_backoff(scope TEXT PRIMARY KEY, not_before TEXT, failures INTEGER, updated_at TEXT)
meta(key TEXT PRIMARY KEY, value TEXT)
```

Конфигурация не дублируется в БД. `whitelisted/source_tag` в cursor — snapshot для аудита; актуальное решение всегда использует текущий config.

Ключевая операция `commit_delivery(dialog, sent_parts, fetched_high_watermark)` выполняет одной SQLite-транзакцией: вставляет ledger-запись для каждого реально отправленного MIME part, затем `UPDATE ... SET last_id = max(last_id, high_watermark)`. До вызова должны успешно уйти все части. Если SMTP сорвался на части N, ledger/cursor не меняются, и весь логический батч может повториться; уже принятые части могут задублироваться — это ожидаемая at-least-once граница. Если ledger insert или commit БД сорвался после SMTP, cursor не движется.

High-watermark вычисляется как maximum ID полного результата `fetch_since`, а не батча. Если адресованных сообщений нет, SMTP/ledger не нужны: cursor безопасно продвигается отдельной монотонной транзакцией до fetched maximum, потому что все выбранные элементы уже классифицированы как echo/dropped. Если есть хотя бы одно адресованное сообщение, high-watermark продвигается только после успешной доставки всех адресованных элементов. Fetch limit означает, что хвост добирается следующими тактами; gaps никогда не синтезируются и не проверяются.

Для исходящего reply порядок: Telegram `send_message` → в одной БД-транзакции echo marker + consumed marker. Краш между send и БД может повторно опубликовать ответ; спецификация требует action-before-consume и запрещает потерю, поэтому ровно-once через два внешних ресурса недостижимо без дополнительного Telegram idempotency API. Это явно принимаемый at-least-once crash window. В штатном повторном poll consumed marker предотвращает дубль.

Retention запускается после успешного такта, не на критическом пути: oldest-first, одновременно по возрасту и максимальному количеству. Удаляются старые ledger, consumed и echo записи; echo — только старше `echo_retention`, которое не превышает общий retention. Cursor и singleton state не очищаются. Ledger purge означает, что очень поздний reply станет недоверенным/нераспознаваемым — это операторски видимая metadata-only запись в логе.

## 6. Детали потоков

### 6.1. Telegram → email

1. Проверить enabled/session/backoff; получить перечень DM и сконфигурированных источников. Для упоминаний `all` нужен обзор доступных channel/group dialogs; для `selected/forced_list` достаточно union whitelist + mention-list.
2. Для каждого dialog/topic прочитать cursor и fetch `id > cursor` с `TG_FETCH_LIMIT`. Ошибка одного peer не откатывает уже завершённые диалоги; backoff scoped по peer/API.
3. Для каждого сообщения в порядке ID: проверить `> cursor`, затем echo identity, затем `is_addressed`. Сохранить maximum fetched ID независимо от результата gate.
4. Собрать максимум один логический batch на dialog/topic. Скачать media адресованных сообщений во временный каталог mode 700. `MediaUnavailable` превращается в placeholder; FloodWait/transient срывает этот dialog cycle и не двигает cursor.
5. HTML renderer экранирует пользовательский текст, затем применяет только поддержанные Telethon entities через whitelist (`strong/em/code/pre/a/blockquote`); произвольный HTML не проходит. Показываются author, `@username`, локализованное время, reply quote (если доступна), source tag и deep-link.
6. Изображения становятся CID inline (`Content-ID`, `multipart/related`); non-image `<= ATTACHMENT_THRESHOLD_BYTES` — attachment; выше — placeholder с name/type/size. Для DM deep-link отсутствует. Public: `https://t.me/<username>/<msg>` или `/<topic>/<msg>`; private supergroup: `https://t.me/c/<internal_id>/<msg>` или `/<topic>/<msg>`.
7. Размер измеряется по окончательно сериализованным MIME bytes, включая base64 overhead. Сначала downgrade крупнейших non-images, затем split только между сообщениями, затем downgrade oversized inline image. Каждый omission имеет placeholder. Split parts получают `(1/N)` и отдельные Message-ID; все относятся к одному dialog.
8. Отправить части последовательно. После успеха всех частей — ledger rows, затем cursor high-watermark. Временные файлы удаляются в `finally`.

Устойчивый Message-ID генерируется один раз на попытку compose и передаётся явно в SMTP. Он уникален (`uuid@B-domain`), но не детерминирован по batch: после неясного SMTP outcome повтор создаёт новый mail и не конфликтует с возможной старой ledger row. Тред ответов разрешается по `In-Reply-To` и всем IDs из `References`.

### 6.2. Email → Telegram и команды

IMAP возвращает сырое письмо и envelope/header metadata через `BODY.PEEK[]`. До классификации применяются `is_auto_or_loop`, точное нормализованное `From == U_ADDRESS`, явный получатель `To/Delivered-To/X-Original-To` содержит `B_ADDRESS`, и not-consumed. Заголовки разворачиваются, CR/LF схлопываются; адреса парсятся стандартной библиотекой.

Parent ledger ищется сначала по нормализованному `In-Reply-To`, затем по каждому Message-ID в `References` от ближайшего к старому. Без ledger письмо игнорируется. Reply text берётся из `text/plain`; при HTML-only преобразуется безопасным HTML-to-text адаптером; процитированный хвост отсекается консервативно. Пустой ответ не публикуется.

Команда — строгая единственная непустая строка в subject или первом body line:

```text
MAILTG ON  [<token>]
MAILTG OFF [<token>]
```

Регистр команды нечувствителен, токен сравнивается `hmac.compare_digest`, лишний текст делает письмо некомандой. Если `COMMAND_TOKEN` задан, отсутствие/ошибка токена всегда reject + metadata log. Команда также обязана быть reply на bridged mail: тем самым сохраняется общий trust predicate `U ∧ on-B ∧ ledger-parent`; session validity и enabled на исполнение команды не влияют.

Обычный reply после trust/ledger требует enabled+valid. После `post_as_user` записываются `(dialog_id, posted_msg_id)` echo и consumed. Вложения email в v1 игнорируются с metadata log. Команда атомарно меняет singleton bridge state; повторное ON/OFF — no-op. Подтверждение отправляется с B на U. Точный момент consume относительно подтверждения вынесен в Q2, поскольку спека одновременно называет действием применение команды и требует подтверждение в постусловии.

### 6.3. Ошибки, backoff и session health

`FloodWait` устанавливает persisted `not_before = now + wait_seconds` для затронутого TG scope. Transient использует exponential backoff `min(max, minimum * 2^(failures-1))` с небольшим jitter; минимум соблюдается, значение сохраняется через рестарт. Успех сбрасывает scope. Scheduler спит до ближайшего due time, но не делает inline retry и не busy-loops.

Session-invalid имеет приоритет над retry: первая auth/session ошибка любой Telethon-операции атомарно ставит `valid=false, notified=false`. Все следующие TG operations блокируются. Notice отправляется email-адаптером; `notified=true` только после SMTP success. При transient SMTP следующий mailbox/maintenance wake-up повторяет notice с backoff. Успешный `setup` после проверки `get_me()` ставит `valid=true, notified=false` и очищает TG backoff.

Mail auth failure и невалидная конфигурация — terminal startup/runtime fault с ненулевым exit для systemd; секреты в exception string редактируются. Peer-not-found изолирует источник и логируется, не инвалидирует session.

## 7. Конфигурация `.env`

Все пути абсолютные и вне репозитория. Значения размеров — целые bytes, интервалы/retention — целые seconds. Дефолты ниже — предлагаемые implementation defaults, поскольку спецификация намеренно оставила числа design/config-слою; Арет должен утвердить их.

```dotenv
# Telegram user access
TG_API_ID=
TG_API_HASH=
TG_SESSION_PATH=/var/lib/mailtg-bridge/telegram
TG_FETCH_LIMIT=100

# Bridge mailbox B: address and credentials
B_ADDRESS=bridge@example.net
B_USERNAME=bridge@example.net
B_PASSWORD=
B_IMAP_HOST=imap.example.net
B_IMAP_PORT=993
B_IMAP_SECURITY=ssl
B_SMTP_HOST=smtp.example.net
B_SMTP_PORT=465
B_SMTP_SECURITY=ssl

# Trusted user mailbox U
U_ADDRESS=user@example.org

# Sources: JSON arrays avoid ambiguous comma escaping
WHITELIST_JSON=["@public_channel","-1001234567890","-1001234567890:42"]
MENTION_POLICY=selected
MENTION_LIST_JSON=["-1001234567890","-1001234567890:42"]

# Delivery and scheduling
ATTACHMENT_THRESHOLD_BYTES=10485760
EMAIL_SIZE_LIMIT_BYTES=25165824
COLLECT_INTERVAL_SECONDS=60
SEND_INTERVAL_SECONDS=30
BACKOFF_MIN_SECONDS=30
BACKOFF_MAX_SECONDS=3600
COMMAND_TOKEN=
TIMEZONE=America/Phoenix

# Retention (age and count bounds)
RETENTION_SECONDS=7776000
RETENTION_MAX_LEDGER=50000
RETENTION_MAX_CONSUMED=50000
RETENTION_MAX_ECHO=10000
ECHO_RETENTION_SECONDS=604800

# Runtime/state
STATE_DB_PATH=/var/lib/mailtg-bridge/state.sqlite3
LOCK_PATH=/run/mailtg-bridge/bridge.lock
TEMP_DIR=/var/lib/mailtg-bridge/tmp
LOG_LEVEL=INFO
```

Валидация на старте: обязательные поля, enum, email/address normalization, положительные интервалы/порты/лимиты; `ATTACHMENT_THRESHOLD < EMAIL_SIZE_LIMIT`; `ECHO_RETENTION <= RETENTION`; непустой whitelist item канонизируется в `(peer_id, topic_id?)`; session/db/env permissions не шире 600, parent dirs не шире 700. Пароли, API hash и command token никогда не печатаются. `COMMAND_TOKEN` пустой означает, что дополнительный token отключён, но тройной trust predicate остаётся.

## 8. Запуск и развёртывание

Основной вариант — один long-running systemd service, не timer: он естественно поддерживает разные интервалы, один Telethon client и lifetime flock. Unit использует выделенного Unix-user, `EnvironmentFile=/etc/mailtg-bridge/mailtg-bridge.env`, `StateDirectory=mailtg-bridge`, `RuntimeDirectory=mailtg-bridge`, `UMask=0077`, `Restart=on-failure`, hardening (`NoNewPrivileges`, `PrivateTmp`, ограниченные writable paths). `ExecStart=... python -m mailtg_bridge run`; SIGTERM завершает текущий атомарный шаг, disconnect/logout и release lock.

Альтернатива — systemd timers/cron с `once --kind inbound|mailbox`, но каждый запуск всё равно берёт тот же flock; она хуже из-за повторного Telethon login и сложнее для независимых backoff. Docker опционален: bind-mount env read-only и отдельный persistent volume для session/SQLite, `--user`, `restart unless-stopped`; интерактивный setup запускается разово с TTY на том же volume.

Первичная настройка:

1. Установить пакет/venv, создать внешний env/state dir mode 700 и env mode 600.
2. `python -m mailtg_bridge check-config` проверяет поля, TLS endpoints без вывода секретов и доступность путей.
3. `python -m mailtg_bridge setup` спрашивает phone через stdin, code и 2FA password через `getpass`; создаёт session по `TG_SESSION_PATH`, проверяет `get_me`, chmod 600, отмечает session valid/notified=false.
4. Запустить/enable service и проверить metadata health logs. Повторный setup идемпотентно проверяет действующую session; `--reauthorize` требует явного флага.

## 9. Наблюдаемость и тестовые швы

Логи — структурированные события с operation, source tag/hashed dialog id, counts, duration, cursor before/after, error class и next retry. Запрещены тела Telegram/email, MIME, media names при риске PII, credentials/token/session, полный sender. Session invalid и rejected commands логируются без содержимого/token. Health определяется живым процессом плюс событиями last-success; отдельный `once` даёт exit codes для диагностики.

Обязательные unit-инварианты: все режимы addressing; DM short-circuit; gaps/deleted/echo/gated high-watermark; no cursor on partial send/ledger failure; chronological batch/split; точный MIME limit/CID/plain fallback; public/private/topic links и no DM link; trust/token constant-time; action-before-consume; bounded oldest-first retention; one-shot invalid notice; FloodWait not-before.

Integration tests напрямую соответствуют пяти `scn-*` и используют fake clock, fake Telegram/mail ports и настоящий временный SQLite. Fault injection ставится перед/после SMTP, ledger insert, cursor update, Telegram post и consume commit. Contract tests закрепляют минимально поддержанную версию Telethon и stdlib MIME/IMAP mappings; smoke-тест выполняет authorize/list/fetch/post в тестовом аккаунте только вручную.

## 10. Риски и открытые вопросы к Арету

1. **Bootstrap cursor.** Спека не говорит, доставлять ли историю при первом обнаружении dialog. Предложение: `last_id=0` означает доставить доступный хвост в пределах fetch limit; безопаснее от потери, но может дать исторический шум. Альтернатива — явный `BOOTSTRAP_MODE=tail|history`, default `tail` как в channel-reader.
2. **Consume команды и confirmation.** Считать команду успешно исполненной сразу после persistent toggle (тогда SMTP confirmation retry ведётся отдельно) или только после confirmation? Предложение: toggle + consume одной транзакцией, confirmation как persisted pending notice; иначе SMTP-сбой будет повторно применять idempotent toggle и плодить попытки.
3. **Один batch vs split.** `alg-oversize-degrade` разрешает несколько писем, хотя batch/email связь названа 1:1. Дизайн трактует split как несколько transport parts одного logical batch и пишет ledger на каждый Message-ID. Нужна явная санкция.
4. **Tracked dialogs при mention-policy=all.** Полный обход всех доступных каналов/групп может быть дорогим и раскрывать больше metadata. Утвердить: действительно all dialogs либо только явный discovery-list.
5. **Mention detection.** Telethon `message.mentioned` обычно достаточен, но поведение channel posts, textual `@username` и topics требует fixtures на реальном аккаунте. Уточнить, считать ли простой текстовый `@username` прямым mention, если Telegram не выставил flag/entity.
6. **SMTP ambiguous outcome.** Таймаут после `DATA` может означать принятое письмо; повтор даст дубль. Exactly-once недостижим без provider idempotency. Дизайн выбирает at-least-once в соответствии со спекой.
7. **Reply crash window.** Краш после Telegram post до echo+consume commit может повторить публикацию. Для закрытия нужен pending-outbox/reconciliation механизм, которого нет в контракте Telegram; оставить как остаточный риск или расширить спецификацию.
8. **Retention.** Утвердить предложенные age/count defaults и ожидаемый максимальный срок ответа на старое письмо; после purge reply намеренно игнорируется.
9. **Source identifiers/deep links.** Утвердить формат `WHITELIST_JSON`, canonical peer/topic IDs и преобразование `-100...` в `<internal_chat_id>` для `t.me/c` на реальных fixtures.
10. **Mail security modes.** Разрешить только TLS (`ssl`/`starttls`) и запретить plaintext предлагается как обязательный guardrail; проверить нужного провайдера B.
11. **Дефолтные числа.** Утвердить fetch=100, 60/30 sec циклы, 10 MiB attachment threshold, 24 MiB MIME limit, backoff 30..3600 sec и retention 90 days/50k.

## 11. Порядок будущей реализации после design-gate

1. Domain/config/ports/errors и SQLite migrations/invariant tests.
2. Перенос email commons в адаптеры, MIME composer и oversize tests.
3. Telethon gateway/setup/error classification и contract fixtures.
4. Чистые algorithms и оба application cycle с fault injection.
5. Session-health/backoff/retention, CLI/flock/systemd.
6. Сквозные `scn-*` integration tests, permission/secret/log checks и документация оператора.
