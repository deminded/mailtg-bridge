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
- Статус описания: draft (слой требований сгенерирован, ждёт human-gate → actual)

---

## 2. Общие артефакты
 - `00-glossary.md` # Глоссарий предметной области (19 терминов)

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
 <!-- fd-<slug> не создавалась: связи функций линейны (вход→ledger→ответ), отдельная диаграмма избыточна на MVP -->

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
_Не генерировался (derive layer=req). Ждёт согласования требований и запуска layer=spec._

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

---

### Легенда
 + done — файл создан, содержание актуально
 - draft — файл создан, содержание неполное (весь слой в статусе draft до human-gate)
 ? planned — артефакт запланирован, файла ещё нет
 · (точка) — возможность внутри компонента, не отдельный файл
