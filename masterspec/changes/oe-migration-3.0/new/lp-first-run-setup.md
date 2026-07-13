---
type: load-profile
slug: lp-first-run-setup
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-13
---
# Профиль нагрузки: первичная авторизация Telegram

## Основание
-> fn-first-run-setup/OE-LOAD: разовая операция на развёртывание (население = 1); повторный запуск —
только событийно, при недействительной/отозванной сессии (переавторизация) или явном
`--reauthorize`; нет периодического или пикового потока — это не тактовая функция. Источник: код
`__main__.py` (`setup`/`--reauthorize` — отдельная подкоманда CLI, не входит в цикл `run()`),
`setup.py` (`run_setup`).
