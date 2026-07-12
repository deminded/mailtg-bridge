---
type: component-diagram
slug: cd-mailtg-bridge
factory: mailtg-bridge
status: draft
owner: Евгений
updated: 2026-07-12
---
# Компонентная диаграмма: Мост Telegram ↔ Почта

## Описание
Пять логических компонентов моста и их связь с двумя внешними системами (Telegram — пользовательская
сессия; ящик моста B — SMTP/IMAP) и хранилищем состояния. Оркестратор ведёт такты; шлюз Telegram —
единственный владелец сессии (чтение и публикация); исходящая/входящая почта разнесены; хранилище держит
курсоры, журнал связки, маркеры и состояния.

## Связи между компонентами
- -> cmp-bridge-orchestrator командует тактами: вызывает -> cmp-tg-gateway (сбор/публикация),
  -> cmp-email-out (формирование/отправка), -> cmp-email-in (опрос ящика), читает/пишет -> cmp-state-store.
- -> cmp-tg-gateway ↔ Telegram (внешняя система) по -> api-telegram-userclient; отдаёт сообщения/медиа
  в -> cmp-email-out, принимает текст ответа от -> cmp-email-in для публикации.
- -> cmp-email-out → ящик B (SMTP) по -> api-mailbox-imap-smtp; читает конфигурацию/пишет Message-ID в -> cmp-state-store.
- -> cmp-email-in ← ящик B (IMAP) по -> api-mailbox-imap-smtp; ищет запись связки и ставит маркеры в -> cmp-state-store.
- -> cmp-state-store — общая память всех компонентов (курсоры, журнал связки, маркеры, состояния, конфигурация).

## Диаграмма
```mermaid
flowchart LR
    TG[(Telegram\nuser-сессия)]
    B[(Ящик моста B\nSMTP/IMAP)]
    U[(Адрес пользователя U)]

    subgraph Мост
      ORC[cmp-bridge-orchestrator]
      GW[cmp-tg-gateway]
      EOUT[cmp-email-out]
      EIN[cmp-email-in]
      ST[(cmp-state-store)]
    end

    ORC -->|такт сбора| GW
    ORC -->|формировать/отправить| EOUT
    ORC -->|такт опроса| EIN
    ORC <-->|состояние/курсоры| ST

    GW <-->|api-telegram-userclient| TG
    GW -->|сообщения+медиа| EOUT
    EIN -->|текст ответа| GW

    EOUT -->|api-mailbox-imap-smtp SMTP| B
    B -->|доставка| U
    U -->|ответ/команда| B
    B -->|api-mailbox-imap-smtp IMAP| EIN

    EOUT <-->|Message-ID/конфиг| ST
    EIN <-->|связка/маркеры| ST
    GW <-->|курсор/сессия| ST
```

## Связи
- Компоненты: -> cmp-bridge-orchestrator, -> cmp-tg-gateway, -> cmp-email-out, -> cmp-email-in, -> cmp-state-store
