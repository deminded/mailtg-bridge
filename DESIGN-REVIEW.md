# Design-gate review (Арет) — mailtg-bridge

**Вердикт: APPROVED.** Дизайн корректно реализует ужесточённую спеку, обоснованно переиспользует обкатанное ядро, делает верное улучшение (SQLite вместо JSON-ledger — даёт атомарность ledger→cursor, которой требует at-least-once/high-watermark). Все folded spec-фиксы отражены. Можно в реализацию.

## Ответы на открытые вопросы (Q1–Q11)
1. **Bootstrap cursor:** `tail` по умолчанию (`BOOTSTRAP_MODE=tail|history`, дефолт tail) — как channel-reader; хвост в пределах fetch limit, без исторического шума. ОК.
2. **Consume команды vs confirmation:** toggle + consume ОДНОЙ транзакцией; confirmation — persisted pending notice, ретраится отдельно. Принято (иначе SMTP-сбой плодит повторные toggle). Это и есть ответ на Q2 в маппинге.
3. **Split vs 1:1:** split = несколько transport-частей ОДНОГО логического batch, ledger на каждый Message-ID. Санкционирую (1:1 в спеке = dialog↔batch; split для oversize — транспортный уровень).
4. **mention-policy=all:** НЕ обходить все каналы/группы (дорого, лишняя metadata). Дефолт — явный discovery-list (union whitelist+mention-list); полный `all` — только явным опт-ином. 
5. **Mention detection:** primary — Telethon `message.mentioned`; текстовый `@username` тоже считать mention (консервативно, не терять). Fixtures на реальном аккаунте — на этапе теста.
6. **SMTP ambiguous outcome:** at-least-once (принято, по спеке).
7. **Reply crash window:** принять как остаточный at-least-once риск; consumed-marker гасит дубль при штатном repoll. Pending-outbox в v1 НЕ строить (YAGNI). Зафиксировать в README как известную границу.
8. **Retention defaults:** предложенные (90 дней / 50k) — ОК для v1, помечено Евгению на подтверждение.
9. **Source-id/deep-link формат:** точное `-100…`→`<internal_chat_id>` для `t.me/c` — подтвердить на реальных fixtures (этап теста); tg:// не нужен для 1:1 (ссылки нет).
10. **Mail security:** ТОЛЬКО TLS (ssl/starttls), plaintext запрещён — обязательный guardrail. ОК.
11. **Дефолтные числа:** fetch=100, циклы 60/30с, threshold 10 MiB, MIME-лимит 24 MiB, backoff 30..3600с, retention 90д/50k — принято для v1, ВСЕ помечены Евгению на утверждение (спека намеренно оставила числа конфигу).

## Требования к реализации (гейт 2 — мой ревью кода)
- Строго по DESIGN.md + этим ответам; при расхождении приоритет — спека/verify-ответы.
- Секреты/сессия/токен/тела сообщений — НЕ в логи (редакция), файлы 600/700.
- Чистые алгоритмы — без сети, покрыты unit-инвариантами из §9.
- Переиспользование ядра — переносом поведения + тестами (не import соседних скриптов по пути).
- Прогнать unit-тесты чистых алгоритмов после написания (само-проверка).
