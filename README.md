# Робо&Ты

«От параметров объекта до обоснованного решения по роботизации» — веб-платформа для экспресс-предынвестиционной оценки роботизированных решений.

Рабочий сквозной контур: конкурсные данные → проект объекта → объяснимый подбор → экономика → 2D-план и симуляция → PDF/CSV. Актуальная готовность и ограничения зафиксированы в [STATUS.md](STATUS.md).

## Запуск одной командой

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- приложение: <http://localhost:3000>
- OpenAPI: <http://localhost:8000/docs>
- healthcheck: <http://localhost:8000/health>

Docker Desktop должен быть запущен. Первый старт создаёт схему PostgreSQL миграциями Alembic и загружает seed.

## Демо-сценарий

1. Откройте `/demo` и войдите демо-пользователем.
2. Проверьте параметры склада.
3. Откройте объяснимый подбор и экономику.
4. В 2D-редакторе переместите зоны, сохраните план и запустите симуляцию.
5. Скачайте PDF и CSV на шаге «Отчёт».

| Роль | Логин | Пароль |
|---|---|---|
| пользователь | `demo@robo.local` | `Demo-2026!` |
| администратор | `admin@robo.local` | `Admin-2026!` |

Это только локальные демонстрационные значения. Для внешнего стенда измените пароли и задайте случайный `SECRET_KEY` длиной не менее 32 символов. Production-конфигурация отклоняет стандартный или короткий ключ.

## Локальная разработка без Docker

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Во втором терминале:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

При локальном запуске backend использует SQLite; Docker использует PostgreSQL. PDF гарантированно проверяется в Docker, где установлены Pango и шрифт DejaVu Sans.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m ruff check backend\app backend\tests backend\alembic\versions\9ce12ad2f8b1_add_simulation_schema.py
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m pip_audit -r backend\requirements.txt

cd frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
npm.cmd audit
```

## Безопасность данных

- `input/`, PDF, пользовательские выгрузки, `.env`, пароли и токены не коммитятся.
- Чужой проект возвращает 404; роли и владелец проверяются на backend.
- Неизвестное значение не превращается в ноль или пройденное ограничение.
- PDF формируется без внешних URL; CSV защищён от formula injection.
- Перед публичным стендом замените demo-учётные данные, включите `ENVIRONMENT=production`, TLS и общее хранилище rate limit.

## Обновление seed из `input/`

Исходники не коммитятся. После размещения конкурсных XLSX и CSV:

```powershell
.\.venv\Scripts\python.exe -m pip install openpyxl==3.1.5
.\.venv\Scripts\python.exe scripts\build_seed.py
```

Импорт создаёт 3 типа объектов, 138 определений параметров, 187 уникальных продуктов и 223 отдельных кейса/строки внедрения. Дубликаты `id` в CSV не выдаются за разные продукты.

## Структура

- `backend/` — FastAPI, модели, миграции, подбор, экономика, симуляция, отчёты и тесты;
- `frontend/` — React/TypeScript, React Konva, ECharts и русский интерфейс;
- `data/seed/` — воспроизводимые нормализованные данные;
- `scripts/` — импорт конкурсных файлов;
- `docs/` — источники, архитектура, методики и отчёт передачи;
- `input/` — локальные исходники, исключённые из git.

Полный технический отчёт: [docs/handoff-report-2026-09-21.md](docs/handoff-report-2026-09-21.md). Спецификация локального зрения: [docs/local-vision-model.md](docs/local-vision-model.md).