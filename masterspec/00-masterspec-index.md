---
type: masterspec-index
factory: mailtg-bridge
updated: 2026-07-12
---
# Индекс фабрики: Мост Telegram ↔ Почта (mailtg-bridge)

## 1. Паспорт
- Фабрика: mailtg-bridge — мост между личным аккаунтом Telegram (пользовательский доступ) и почтой
- Владелец: Евгений
- Дата создания индекса: 2026-07-12
- Статус описания: draft (слои требований и спецификаций сгенерированы, ждут human-gate → actual)

---

## 2. Общие артефакты
 - `00-glossary.md` # Глоссарий предметной области (23 термина)

---

## 3. Слой требований

### 3.1. Паспорт АС/ФП
 - `01-requirements/01-system/as-mailtg-bridge.md` # Мост Telegram ↔ Почта

### 3.2. Функции АС/ФП

#### Входящий поток (Telegram → почта)
 - `01-requirements/02-functions/fn-dm-batch-to-email.md` # Доставка личных сообщений батчем на почту
 - `01-requirements/02-functions/fn-channel-update-to-email.md` # Доставка обновлений каналов/групп (белый список/упоминание)
 - `01-requirements/02-functions/fn-media-in-email.md` # Представление медиа и вложений в письме

#### Исходящий поток (почта → Telegram)
 - `01-requirements/02-functions/fn-email-reply-to-tg.md` # Публикация ответа из почты в Telegram от лица пользователя

#### Управление и инициализация
 - `01-requirements/02-functions/fn-bridge-control-by-email.md` # Управление мостом письмом (вкл/выкл)
 - `01-requirements/02-functions/fn-first-run-setup.md` # Первичная авторизация Telegram и порождение сессии

### 3.3. Нефункциональные требования
 - `01-requirements/03-nfr/nfr-deployability.md` # Развёртываемость (≤10 мин, смена провайдера конфигом)
 - `01-requirements/03-nfr/nfr-portability.md` # Провайдер-нейтральность и открытость
 - `01-requirements/03-nfr/nfr-operability.md` # Эксплуатируемость (неинтерактивность, периодичность)
 - `01-requirements/03-nfr/nfr-privacy.md` # Приватность (нет тел/секретов в логах)
 - `01-requirements/03-nfr/nfr-security.md` # Безопасность сессии и учётных данных

### 3.4. Бизнес- и внутренние правила
 - `01-requirements/04-rules/rules-gating.md` # Гейтинг адресованности (что доставляется)
 - `01-requirements/04-rules/rules-delivery.md` # Формирование и гранулярность доставки (батч/медиа/вложения)
 - `01-requirements/04-rules/rules-integrity.md` # Целостность состояния, дедуп, анти-петля
 - `01-requirements/04-rules/rules-control.md` # Управление мостом письмом и авторизация команды
 - `01-requirements/04-rules/rules-security.md` # Безопасность сессии, кредов и логов

### 3.5. Диаграмма окружения и функциональная диаграмма
 - `01-requirements/05-landscape/context-mailtg-bridge.md` # Диаграмма окружения

### 3.6. Концептуальная модель данных
 - `01-requirements/06-data-model/cdm-bridge.md` # Домен моста (сущности + состояния/переходы)

### 3.7. Справочники и классификаторы
 - `01-requirements/07-dictionaries/dict-source-type.md` # Тип источника диалога (dm/channel/group/topic)
 - `01-requirements/07-dictionaries/dict-media-disposition.md` # Способ представления вложения в письме

### 3.8. Приёмочные тесты
 - `01-requirements/08-test-cases/tc-acc-dm-delivery.md` # Доставка личка батчем (-> fn-dm-batch-to-email)
 - `01-requirements/08-test-cases/tc-acc-channel-gating.md` # Гейтинг каналов/групп (-> fn-channel-update-to-email)
 - `01-requirements/08-test-cases/tc-acc-email-reply.md` # Ответ из почты в TG (-> fn-email-reply-to-tg)
 - `01-requirements/08-test-cases/tc-acc-media-rendering.md` # Медиа/вложения в письме (-> fn-media-in-email)
 - `01-requirements/08-test-cases/tc-acc-antiloop-dedup.md` # Анти-петля/дедуп/перезапуск (-> fn-dm-batch-to-email, fn-email-reply-to-tg)
 - `01-requirements/08-test-cases/tc-acc-bridge-control.md` # Управление вкл/выкл (-> fn-bridge-control-by-email)
 - `01-requirements/08-test-cases/tc-acc-deploy-and-security.md` # Деплой + гигиена сессии/логов (-> fn-first-run-setup)

---

## 4. Слой спецификаций

### 4.1. Компоненты и их возможности
 - `02-specifications/01-components/cmp-bridge-orchestrator.md` # Оркестратор моста (поллинг-цикл)
   · cap-apply-backoff — отступ при FloodWait/преходящих ошибках без busy-loop
   · cap-assemble-dialog-batch — группировка сообщений диалога за такт в один батч
   · cap-enforce-delivery-gates — проверка «мост включён И сессия действительна»
   · cap-run-inbound-cycle — такт сбора входящих (Telegram → письмо)
   · cap-run-mailbox-cycle — такт опроса ящика (ответы/команды)

 - `02-specifications/01-components/cmp-email-in.md` # Входящая почта (опрос ящика B, ответы и команды)
   · cap-authenticate-sender — единый предикат доверия (U ∧ на B ∧ in-reply-to)
   · cap-classify-message — ответ / команда / игнор
   · cap-mark-consumed — однократное потребление письма
   · cap-poll-b-imap — выборка новых писем на ящике B
   · cap-resolve-ledger — In-Reply-To → запись связки → диалог

 - `02-specifications/01-components/cmp-email-out.md` # Исходящая почта (формирование и отправка с ящика B)
   · cap-build-deeplink — глубокая ссылка по типу источника (личка — без ссылки)
   · cap-compose-batch-email — HTML+текст письмо из батча
   · cap-degrade-on-oversize — деградация/дробление при превышении лимита
   · cap-render-media — инлайн-изображение / файл / текстовое указание
   · cap-send-from-b — SMTP-отправка с B на U с заголовками треда
   · cap-send-notice — подтверждения команд и уведомление о сессии

 - `02-specifications/01-components/cmp-state-store.md` # Хранилище состояния (курсоры, журнал связки, состояния, конфигурация)
   · cap-manage-bridge-state — переключатель вкл/выкл (singleton, персистентный)
   · cap-manage-consume-markers — маркеры потреблённых писем (ограниченные)
   · cap-manage-cursor — курсор диалога (монотонный, продвижение после отправки)
   · cap-manage-ledger — журнал связки (добавление/поиск/retention)
   · cap-manage-session-health — здоровье сессии (действительна/недействительна, блокирующее)
   · cap-read-config — доступ к валидированной конфигурации

 - `02-specifications/01-components/cmp-tg-gateway.md` # Шлюз Telegram (пользовательская сессия)
   · cap-apply-addressing-gate — гейт: личка всегда, канал/группа по списку∨упоминанию
   · cap-detect-own-echo — отсев собственного эха (анти-петля)
   · cap-download-media — скачивание вложений сообщения
   · cap-fetch-since-cursor — выборка новых сообщений диалога после курсора
   · cap-post-as-user — публикация ответа в диалог от лица пользователя
   · cap-surface-session-errors — классификация ошибок MTProto (FloodWait/преходящая/сессия)

### 4.2. Сценарии
 - `02-specifications/02-scenarios/scn-control-command.md` # Управление мостом письмом (включить/выключить)
 - `02-specifications/02-scenarios/scn-first-run-setup.md` # Первичная авторизация Telegram (интерактивный setup → сессия)
 - `02-specifications/02-scenarios/scn-inbound-collect-cycle.md` # Такт сбора входящих (Telegram → письмо-батч)
 - `02-specifications/02-scenarios/scn-outbound-reply.md` # Публикация ответа из почты в Telegram
 - `02-specifications/02-scenarios/scn-session-invalid-alert.md` # Недействительная сессия — остановка и уведомление

### 4.3. Алгоритмы
 - `02-specifications/03-algorithms/alg-addressing-gate.md` # Гейт адресованности (что доставляется)
 - `02-specifications/03-algorithms/alg-backoff-on-floodwait.md` # Отступ при FloodWait и преходящих ошибках
 - `02-specifications/03-algorithms/alg-batch-per-dialog-cycle.md` # Батчинг «диалог за такт» и дисциплина курсора
 - `02-specifications/03-algorithms/alg-dedup-idempotency.md` # Дедуп доставки, анти-петля, идемпотентность приёма
 - `02-specifications/03-algorithms/alg-oversize-degrade.md` # Деградация при превышении лимита размера письма

### 4.5. Внешние API
 - `02-specifications/04-apis/external/api-mailbox-imap-smtp.md` # Ящик моста B — SMTP/IMAP (usage-контракт)
 - `02-specifications/04-apis/external/api-telegram-userclient.md` # Пользовательский клиент Telegram (usage-контракт MTProto)

### 4.6. Схемы данных
 - `02-specifications/05-data/data-bridge-store.md` # Персистентное состояние моста

### 4.7. Диаграммы
 - `02-specifications/06-diagrams/cd-mailtg-bridge.md` # Компонентная диаграмма моста

### 4.9. Интеграционные тесты
 - `02-specifications/08-test-cases/tc-int-inbound-collect-cycle.md` # Такт сбора (гейт+батч+медиа+деградация+дедуп)
 - `02-specifications/08-test-cases/tc-int-outbound-reply.md` # Ответ из почты в TG (доверие+маршрутизация+идемпотентность)
 - `02-specifications/08-test-cases/tc-int-control-command.md` # Управление вкл/выкл (доверие+токен+идемпотентность)
 - `02-specifications/08-test-cases/tc-int-session-invalid-alert.md` # Недействительная сессия (стоп+уведомление, без зацикливания)

---

## 5. Слой кодовой базы (LLD)
_Не генерировался._

---

## 6. Решения (ADR)
 - `04-decisions/adr-001-python-core-reuse.md` # Реализация на существующем питоновском ядре (accepted)
 - `04-decisions/adr-002-telethon-hybrid-auth.md` # Гибридная авторизация Telegram (accepted)

---

## 7. Белые пятна и открытые вопросы
- Q4 (авторизация Telegram в quick-deploy) — РАЗРЕШЁН: гибрид (интерактивный setup → headless-сервис), см. -> adr-002-telethon-hybrid-auth.
- Q5 (reply на конкретное TG-сообщение) — СНЯТ решением по гранулярности: ответ уходит в диалог целиком; reply-to сообщения — задел версии 2.
- Мера доступности приёма (SLA) намеренно не задана (best-effort поллинг) — помечена missing-business в -> nfr-operability, назначается владельцем при необходимости.
- Веб-диск для крупных вложений — задел версии 2 (значение `weblink` в -> dict-media-disposition пока не активно).
- Дефолтные значения конфигурации (порог вложений, лимит письма, retention, интервалы сбора/отправки, минимальный отступ backoff) — задать в примере конфигурации при поставке (DEFERRED-TO-SPEC/config, см. route-run-spec.md).
- Формат физического хранения состояния (единый файл vs встроенное key-value) — на слой кода (dmap); на спеке зафиксированы логические инварианты и «без шифрования» (принятый остаточный риск).

---

### Легенда
 + done — файл создан, содержание актуально
 - draft — файл создан, содержание неполное (весь слой в статусе draft до human-gate)
 ? planned — артефакт запланирован, файла ещё нет
 · (точка) — возможность внутри компонента, не отдельный файл
