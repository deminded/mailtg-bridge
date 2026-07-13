---
type: scenario-trace
slug: trace-first-run-setup
factory: mailtg-bridge
status: draft
updated: 2026-07-13
generated: true
---
# Code Trace: первичная авторизация Telegram

## Сценарий
- **Спецификация:** -> scn-first-run-setup
- **Триггер в коде:** `src/mailtg_bridge/__main__.py:execute` — подкоманда `setup` с optional `--reauthorize`.

## Цепочка вызовов

| # | Шаг сценария | Компонент | Code Unit | Kind | Файл | Описание |
|---|---|---|---|---|---|---|
| 1 | 1 | -> cmp-state-store | `load()` / `Settings.from_env()` | call | `src/mailtg_bridge/__main__.py:load`; `src/mailtg_bridge/config.py:Settings.from_env` | Читает и валидирует конфигурацию и абсолютные runtime paths. |
| 2 | 2 | -> cmp-tg-gateway | `run_setup()` / `authorize_interactive()` | external-call | `src/mailtg_bridge/setup.py:run_setup`; `src/mailtg_bridge/telegram.py:authorize_interactive` | Запрашивает phone/code, а при 2FA — password через getpass. |
| 3 | 3 | -> cmp-state-store | `authorize_interactive()` cleanup | call | `src/mailtg_bridge/telegram.py:authorize_interactive` | Закрывает client и chmod существующих session candidates в 0600. |
| 4 | 4 | -> cmp-state-store | `SQLiteStore.set_session()` | db-query | `src/mailtg_bridge/state.py:SQLiteStore.set_session` | После успеха устанавливает valid=true, notified=false и сбрасывает TG backoff. |

## Ветвления в коде

| Условие (из сценария) | Файл | Строка | Как реализовано |
|---|---|---|---|
| Сессия уже авторизована и reauthorize=false | `src/mailtg_bridge/telegram.py` | 92 | Возвращает `get_me()` без запроса кода. |
| Telegram требует 2FA | `src/mailtg_bridge/telegram.py` | 95 | `SessionPasswordNeededError` переключает на password callback. |
| Явная переавторизация | `src/mailtg_bridge/__main__.py` | 19 | CLI flag передаётся до `authorize_interactive`. |

## Обработка ошибок

| Ошибка (из сценария) | Файл | Строка | Механизм |
|---|---|---|---|
| Ошибка code/password/API | `src/mailtg_bridge/telegram.py` | 91 | Исключение выходит в CLI; `finally` отключает client и ограничивает права найденного session-файла. |
| Второй экземпляр setup | `src/mailtg_bridge/__main__.py` | 45 | Общий `LifetimeLock` отклоняет конкурирующий процесс. |

## Маппинг контракта живой эксплуатации

| Грань требования | Владелец в спецификации | Code Unit / конфигурация | Автотест | Live/e2e evidence или остаточный риск | Статус |
|---|---|---|---|---|---|
| -> fn-first-run-setup/OE-LOAD | -> lp-first-run-setup | `src/mailtg_bridge/__main__.py:parser`; `src/mailtg_bridge/__main__.py:execute` | — | Setup — отдельная событийная CLI-команда, не часть периодического цикла; есть `--reauthorize`. | implemented |
| -> fn-first-run-setup/OE-INPUT | -> scn-first-run-setup | `src/mailtg_bridge/setup.py:run_setup`; `src/mailtg_bridge/telegram.py:authorize_interactive` | — | Phone/code идут через terminal input, 2FA password — через `getpass` без эха. | implemented |
| -> fn-first-run-setup/OE-EVIDENCE | -> scn-first-run-setup | `src/mailtg_bridge/telegram.py:authorize_interactive`; `src/mailtg_bridge/orchestrator.py:BridgeService.invalidate_session` | `tests/contract/test_telegram.py:test_error_mapping_and_source` | Успех и invalid-alert имеют след, но при ошибке Telethon уже созданный session candidate не удаляется; обещание «файл не создаётся» не обеспечено. | not-implemented |
| -> fn-first-run-setup/OE-SECURITY | -> scn-first-run-setup | `src/mailtg_bridge/telegram.py:authorize_interactive`; `src/mailtg_bridge/setup.py:run_setup` | — | chmod 0600 и password-without-echo есть; запрета session path внутри репозитория и обязательного userbot warning нет. | not-implemented |
| -> fn-first-run-setup/OE-RESILIENCE | -> scn-first-run-setup | `src/mailtg_bridge/orchestrator.py:BridgeService.invalidate_session`; `src/mailtg_bridge/locking.py:LifetimeLock.acquire`; `src/mailtg_bridge/setup.py:run_setup` | `tests/unit/test_runtime.py:test_lock_exclusive_and_private` | Blocking state, notified flag, reauthorize и общий single-instance lock реализованы. | implemented |
| -> fn-first-run-setup/OE-DELIVERY | -> api-mailbox-imap-smtp | `src/mailtg_bridge/orchestrator.py:BridgeService.invalidate_session`; `src/mailtg_bridge/mail_out.py:SmtpMailer.send_notice` | — | Notice отмечается notified только после SMTP send; один invalid episode не спамит. | implemented |

## Висячие пятна

| Тип | Грань | Что отсутствует |
|---|---|---|
| negative | -> fn-first-run-setup/OE-EVIDENCE | Error path не удаляет частично/заранее созданный Telethon session-файл, поэтому негативная гарантия не доказана кодом. |
| missing | -> fn-first-run-setup/OE-SECURITY | `TG_SESSION_PATH` проверяется только на абсолютность: нет проверки «вне репозитория» и runtime warning о риске userbot. |

## Связи
- Сценарий: -> scn-first-run-setup
- Компоненты: -> cmp-tg-gateway, -> cmp-state-store

