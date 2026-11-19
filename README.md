# cloud-folder

Спрощений аналог Google Drive. Файли зберігаються в особистому просторі на віддаленому сервері: їх можна переглядати, вивантажувати, завантажувати й видаляти. Обраною локальною папкою можна синхронізуватися з десктоп- і веб-клієнта. Сервер разом із веб-клієнтом розгортається одним Docker-контейнером: на Render або через Docker Compose.

Можливості:

- реєстрація та вхід, у кожного користувача свій простір;
- атрибути файлу: ім'я, створено, змінено, хто вивантажив, хто редагував, розмір. Будь-яку колонку, крім імені, можна приховати;
- перегляд вмісту: `.xml` як текст, `.png` як зображення;
- сортування за датою і часом зміни (▲/▼) і фільтр: усі, `.java` або `.png`;
- drag-n-drop для вивантаження;
- двостороння синхронізація папки: при конфлікті зберігаються обидві версії.

## Стек

| Компонент | Технологія |
|---|---|
| Бекенд | Python, FastAPI. Шари: `app` (HTTP) → `services` → `db` / `storage`, без ORM |
| Вебклієнт | Vue 3 + Vite (SPA), `fetch`, File System Access API для синхронізації |
| Десктоп | Python, PySide6 (Qt 6), MVVM, `QFileSystemWatcher` |
| База даних | SQLite, вміст файлів лежить окремо на диску (`data/blobs/`) |
| Автентифікація | JWT (HS256), паролі PBKDF2-SHA256 |
| Розгортання | Docker (двоетапна збірка), Render Blueprint, Docker Compose |
| CI | GitHub Actions: pytest, Vitest, збірка SPA, smoke-тест Docker-образу |

## Структура репозиторію

```text
cloudfolder/core/      спільне ядро: моделі, правила перегляду/сортування/фільтра (variant.py), синхронізація (sync.py)
cloudfolder/server/    REST API: app, services, db (SQLite), storage (LocalFileStorage)
cloudfolder/desktop/   десктоп-клієнт: api_client, viewmodel, sync_engine, main_window
web/                   веб-клієнт (Vue 3 + Vite) і тести Vitest
tests/                 тести pytest: операції сортування/фільтра, синхронізація, view-модель, API
docs/                  UML-діаграми (Mermaid: src/*.mmd → img/) і звіти (.tex + .pdf)
scripts/               seed_demo.py — демо-дані
REQUIREMENTS.md        вимоги до системи (варіант 12), архітектура та алгоритм синхронізації
pyproject.toml         залежності Python (сервер; групи desktop і dev) і налаштування pytest
Dockerfile             образ сервера + зібраний веб-клієнт
docker-compose.yml     локальне / VPS-розгортання з постійним томом
render.yaml            Render Blueprint
```

## Початок роботи

Команди нижче для Windows (PowerShell). На Linux/macOS замініть `.venv\Scripts\` на `.venv/bin/`.

### Залежності

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[desktop,dev]"
cd web; npm install; npm run build; cd ..
```

Без додаткових груп (`pip install -e .`) встановлюються лише залежності сервера. Група `desktop` додає PySide6 і httpx для десктоп-клієнта, `dev` — pytest і pillow для тестів і демо-даних.

### Сервер

```powershell
.venv\Scripts\python -m cloudfolder.server --port 8000
```

Сервер одночасно роздає зібраний веб-клієнт на http://127.0.0.1:8000/. Аргументи: `--host`, `--port`, `--data` (каталог даних, за замовчуванням `data/`).

### Десктоп-клієнт

```powershell
.venv\Scripts\python -m cloudfolder.desktop --server http://127.0.0.1:8000
```

### Вебклієнт у режимі розробки

```powershell
cd web
npm run dev     # http://localhost:5173, запити /api проксіюються на :8000
npm run build   # збірка в web/dist
```

### Демо-дані

```powershell
.venv\Scripts\python scripts\seed_demo.py data\demo
.venv\Scripts\python -m cloudfolder.server --port 8000 --data data\demo
```

Демо-користувач: `Maryna` / `demo123`.

## Тести

```powershell
.venv\Scripts\python -m pytest   # 40 тестів
cd web; npm test                 # 14 тестів
```

## REST API

| Метод | Шлях | Опис |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | реєстрація / вхід → JWT |
| GET | `/api/variant` | правила перегляду, сортування й фільтра (також health check) |
| GET | `/api/files?sort=modified_at&order=asc\|desc&type=.java\|.png` | список файлів з атрибутами |
| POST | `/api/files` (multipart) | вивантаження; те саме ім'я = редагування |
| GET | `/api/files/{id}/content[?download=true]` | вміст файлу |
| DELETE | `/api/files/{id}` | видалення |

## Конфігурація

Секрети передаються через змінні середовища. Для Docker Compose їх можна покласти у файл `.env` поруч із `docker-compose.yml`, він у `.gitignore`. Секрети не комітяться.

| Змінна | Призначення |
|---|---|
| `CLOUDFOLDER_SECRET` | ключ підпису JWT. Якщо не задано, генерується у `<data>/secret.key` |
| `CLOUDFOLDER_DATA` | каталог із базою SQLite і вмістом файлів |
| `PORT` | порт у контейнері (задає Render) |

## Розгортання

### Docker Compose

Підходить для будь-якого ПК чи VPS. Дані зберігаються в іменованому томі `cloudfolder-data`.

```powershell
docker compose up -d --build   # http://localhost:8000
```

Після оновлення коду достатньо повторити ту саму команду: Compose перезбере образ і перезапустить контейнер, а дані в томі залишаться.

### Render

Дає публічний доступ через HTTPS. Підключіть репозиторій у Render → **New → Blueprint**, конфігурація береться з `render.yaml`. Render сам генерує `CLOUDFOLDER_SECRET`, а кожен push у `main` перерозгортає сервіс.

Обмеження безкоштовного тарифу:

- диск тимчасовий: база й файли зникають після перезапуску чи нового розгортання. Щоб дані зберігалися, використовуйте Docker Compose або платний диск Render;
- після ~15 хв без запитів сервіс засинає, і перший запит триває ~30–60 с.

## Документація

```text
docs/diagrams-uml/      UML-діаграми: src/*.mmd (Mermaid), img/ (PNG), report-ua.tex/.pdf
docs/desktop-report/    звіт про десктоп-клієнт + img/screenshots/
docs/web-report/        звіт про веб-клієнт + img/screenshots/
docs/comparison-report/ порівняльний аналіз десктоп- і веб-версії
```

PDF зі `.tex` збирається XeLaTeX (наприклад, в Overleaf: компілятор XeLaTeX, завантажити папку звіту разом з `img/`).
