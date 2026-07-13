---
type: load-profile
slug: lp-email-reply-to-tg
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-13
---
# Профиль нагрузки: публикация ответа из почты в Telegram

## Основание
-> fn-email-reply-to-tg/OE-LOAD: ящик моста B опрашивается целиком каждый такт
(`SEND_INTERVAL_SECONDS`, дефолт 30 с): IMAP-выборка `SEARCH ALL` возвращает все письма ящика,
включая уже обработанные — стоимость такта ≈ O(размер INBOX ящика B), а не только O(новые письма);
уже потреблённые письма (`consumed_mail`) пропускаются логически без публикации, но физически
перечитываются каждый такт. Рост ящика ограничивается только операторской гигиеной/командой `purge`
(retention), не самим циклом опроса. Источник: код `mail_in.py` (`ImapMailbox.poll` —
`m.uid("search",None,"ALL")`), `config.py` (`SEND_INTERVAL_SECONDS`), `state.py` (`is_consumed`,
`purge_retention`).
