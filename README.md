# Робо&Ты

«От параметров объекта до обоснованного решения по роботизации» — веб-платформа для экспресс-предынвестиционной оценки роботизированных решений.

Текущий инкремент реализует самый важный сквозной контур: импорт конкурсных данных, проект объекта, объяснимый подбор и сравнение текущей работы, покупки и RaaS. Статус остальных функций честно зафиксирован в [STATUS.md](STATUS.md).

## Запуск одной командой

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- приложение: <http://localhost:3000>
- OpenAPI: <http://localhost:8000/docs>
- healthcheck: <http://localhost:8000/health>

Docker Desktop должен быть запущен. Первый старт создаёт схему PostgreSQL миграцией Alembic и загружает seed.

## Демо-аккаунты

| Роль | Логин | Пароль |
|---|---|---|
| пользователь | `demo@robo.local` | `Demo-2026!` |
| администратор | `admin@robo.local` | `Admin-2026!` |

Это только локальные демонстрационные значения. Для любого внешнего стенда измените все пароли и `SECRET_KEY` в `.env`.

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

При локальном запуске backend использует SQLite; Docker использует PostgreSQL.

## Проверки

```powershell
cd backend
..\.venv\Scripts\python.exe -m ruff check --no-cache app tests
..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider

cd ..\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
```

## Обновление seed из `input/`

Исходники не коммитятся. После размещения конкурсных XLSX и CSV:

```powershell
.\.venv\Scripts\python.exe -m pip install openpyxl==3.1.5
.\.venv\Scripts\python.exe scripts\build_seed.py
```

Импорт создаёт 3 типа объектов, 138 определений параметров, 187 уникальных продуктов и 223 отдельных кейса/строки внедрения. Дубликаты `id` в CSV не выдаются за разные продукты.

## Структура

- `backend/` — FastAPI, модели, миграция, подбор, экономика и тесты;
- `frontend/` — React/TypeScript, русский интерфейс и тесты;
- `data/seed/` — воспроизводимые нормализованные данные;
- `scripts/` — импорт конкурсных файлов;
- `docs/` — источники, архитектура и методики;
- `input/` — локальные исходники, исключённые из git.

