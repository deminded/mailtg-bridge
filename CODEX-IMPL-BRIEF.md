# Codex implementation-gate brief — mailtg-bridge

Ты — РЕАЛИЗАТОР (gpt-5.6-sol). ГЕЙТ РЕАЛИЗАЦИИ: напиши Python-код mailtg-bridge СТРОГО по одобренному дизайну. Арет ревьюит код после (гейт 2).

## Контракт (читай в порядке приоритета)
1. `/home/claude-user/mailtg-bridge/DESIGN.md` — чертёж, следуй ему.
2. `/home/claude-user/mailtg-bridge/DESIGN-REVIEW.md` — мои ответы Q1–Q11, применяй их.
3. При конфликте приоритет — спека: `/home/claude-user/mailtg-bridge/masterspec/02-specifications/` + `masterspec/verify-response-*.md`.

## Переиспользование (перенос поведения, НЕ import соседних скриптов по пути; DESIGN §4)
Изучи и перенеси из: `/home/claude-user/channel-reader/reader.py` (Telethon-поллинг, per-dialog cursor); `/home/claude-user/de-agent-commons/src/agentcommons/email.py` (TLS IMAP/SMTP, RFC2047, is_allowed, is_auto_or_loop, MessageLedger-контракт, send_email); `/home/claude-user/email_poller.py` (high-watermark/неперешагивание сбоя, нормализация заголовков); `/home/claude-user/arete-userbot/` (Telethon auth phone/code/2FA, get_messages/send/download_media).

## Построить (в корне `/home/claude-user/mailtg-bridge/`)
Полный пакет по DESIGN §2: `src/mailtg_bridge/*` (config, domain, errors, ports, orchestrator, algorithms, state, telegram, mail_in, mail_out, commands, locking, logging, setup, __main__), `deploy/`, `tests/` (unit/integration/contract), `pyproject.toml`, `README.md`, `.env.example`. Python 3.11+.

## Порядок (DESIGN §11)
1) domain/config/ports/errors + SQLite migrations и invariant-тесты; 2) email-адаптеры + MIME composer + oversize; 3) Telethon gateway/setup/классификация ошибок; 4) чистые algorithms + оба application-цикла; 5) session-health/backoff/retention + CLI/flock/systemd; 6) integration-тесты + проверки permission/secret/log + README.

## Дисциплина (урок Sol 12.07)
- ЧЕКПОИНТ: пиши каждый модуль ПОЛНОСТЬЮ на диск перед следующим; не держи весь код только в рассуждении. Частичный прогресс должен пережить обрыв.
- Если чувствуешь, что затягивается — ПРИОРИТЕТ рабочему ядру (config, state, adapters, algorithms, оба цикла, CLI/flock) над исчерпывающими тестами: сперва работающий мост, потом полное покрытие.
- НЕ трогай `masterspec/` (это спека). Код — в src/, tests/, deploy/.
- Секреты/сессия/токен/тела сообщений НИКОГДА в логи (редакция); файлы 600/700.

## Само-проверка
После чистых algorithms и их unit-тестов — создай venv при нужде и прогони `python -m pytest tests/unit -q`, почини падения. Сообщи результат тестов.

Итог хода: какие модули готовы, результат тестов, что осталось, любые отклонения от DESIGN с причиной.
