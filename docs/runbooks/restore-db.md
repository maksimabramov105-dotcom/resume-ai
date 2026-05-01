# Runbook: Restore Database

Применимо к: `bot.db` (Telegram bot) и `autoapply.db` (AutoApply).

---

## Шаг 0 — Когда запускать

- БД повреждена (`PRAGMA integrity_check` возвращает что-то кроме `ok`)
- Случайное удаление данных
- Ошибка миграции
- Сервер упал в момент записи

---

## Шаг 1 — Остановить сервисы (ОБЯЗАТЕЛЬНО)

```bash
systemctl stop resumeaibot autoapply autoapply-worker
```

---

## Шаг 2 — Выбрать бэкап

```bash
ls -lt /opt/resumeaibot/backups/*.db | head -20
```

Формат имён: `bot.YYYY-MM-DD-HHMM.db` / `autoapply.YYYY-MM-DD-HHMM.db`

---

## Шаг 3 — Проверить целостность бэкапа

```bash
# Замените <backup_file> на нужный файл
sqlite3 /opt/resumeaibot/backups/<backup_file> "PRAGMA integrity_check;"
```

Вывод должен быть `ok`. Если нет — берите более ранний бэкап.

---

## Шаг 4 — Переименовать текущую БД (сохранить на случай ошибки)

```bash
mv /opt/resumeaibot/bot.db        /opt/resumeaibot/bot.db.broken.$(date +%F-%H%M)
mv /opt/resumeaibot/autoapply.db  /opt/resumeaibot/autoapply.db.broken.$(date +%F-%H%M)
```

---

## Шаг 5 — Восстановить

```bash
# bot.db
sqlite3 /opt/resumeaibot/backups/bot.YYYY-MM-DD-HHMM.db \
    ".backup '/opt/resumeaibot/bot.db'"

# autoapply.db
sqlite3 /opt/resumeaibot/backups/autoapply.YYYY-MM-DD-HHMM.db \
    ".backup '/opt/resumeaibot/autoapply.db'"
```

---

## Шаг 6 — Проверить целостность восстановленной БД

```bash
sqlite3 /opt/resumeaibot/bot.db       "PRAGMA integrity_check;"
sqlite3 /opt/resumeaibot/autoapply.db "PRAGMA integrity_check;"
```

Оба должны вернуть `ok`.

---

## Шаг 7 — Запустить сервисы

```bash
systemctl start resumeaibot autoapply autoapply-worker
sleep 5
systemctl status resumeaibot autoapply autoapply-worker --no-pager | grep Active
```

---

## Шаг 8 — Проверить health

```bash
curl -fsS http://localhost:8000/api/health
curl -fsS http://localhost:8080/api/health
```

Оба должны вернуть `{"status":"ok",...}`.

---

## Шаг 9 — Удалить сломанный файл (после подтверждения работы)

```bash
rm /opt/resumeaibot/bot.db.broken.*
rm /opt/resumeaibot/autoapply.db.broken.*
```

---

## Тест (без остановки сервисов)

Безопасная проверка бэкапа в `/tmp`:

```bash
sqlite3 /opt/resumeaibot/backups/bot.YYYY-MM-DD-HHMM.db \
    ".backup '/tmp/test_restore.db'"
sqlite3 /tmp/test_restore.db "PRAGMA integrity_check;"
rm /tmp/test_restore.db
```

---

## Бэкап-файлы в S3 (если настроен offsite)

```bash
# Скачать из S3:
aws s3 cp s3://${AWS_BACKUP_BUCKET}/resumeaibot/bot.YYYY-MM-DD-HHMM.db \
    /opt/resumeaibot/backups/
```
