# CLAUDE.md — Scraping_Russia

Мониторинг рынка керамической плитки России для **ОАО "КЕРАМИН"**.
Парсинг 4 ритейлеров → объединение → гармонизация → дашборд (Streamlit + Supabase).

---

## Структура проекта

```
Scraping_Russia/
├── LeroyMerlin/          LemanaPRO.py + data_MM.YYYY_Tiles_LemanaPRO.json
├── Obi_selenium/         Obi_selenium.py + data_MM.YYYY_plitka_plitka_i_keramogranit_Москва_obi.json
├── Petrovich/            Petrovich.py + data_MM.YYYY_plitka_Petrovich.json
├── KeramogranitRU/       KeramogranitRu.py + data_MM.YYYY_KeramogranitRu.json
├── MERGED_RUSSIA/
│   ├── Main_scraping_Russia.py     # Объединение всех источников
│   ├── harmonization.py            # Гармонизация полей (v2.2)
│   ├── migrate_to_two_tables.py    # Одноразовая миграция data_finally.json → products/prices
│   ├── products.json               # База товаров — статика (в .gitignore)
│   ├── prices.json                 # История цен и остатков (в .gitignore)
│   └── data_finally.json           # УСТАРЕВШИЙ — временно, будет удалён (в .gitignore)
├── dashboard/
│   ├── dashboard.py                # Streamlit-дашборд (читает tiles_v2)
│   ├── upload_to_supabase.py       # Загрузка в Supabase (upsert, два стола)
│   ├── create_table.sql            # Старая схема tiles (устарела)
│   ├── create_tables_v2.sql        # Актуальная схема: products + prices + tiles_v2
│   └── .env                        # SUPABASE_URL, SUPABASE_KEY (не в git)
└── requirements.txt
```

---

## Источники данных

| Источник | Остатки | Онлайн-заказ | Примечания |
|---|---|---|---|
| **LemanaPRO** | Да | Да | Цену считать: box_price / packaging_m2 |
| **OBI** | Да | Нет | Формат из полей Длина/Ширина (в см) |
| **Petrovich** | Да | Нет | Размеры в мм → делить на 10; скидка считается от old_price |
| **Keramogranit_RU** | **Нет** | Нет | total_stock / packaging / total_base_stock = None всегда |

---

## Запуск

### Первичная настройка (один раз)

```bash
# 1. Применить новую схему в Supabase (SQL Editor)
#    Выполнить содержимое dashboard/create_tables_v2.sql

# 2. Конвертировать существующий data_finally.json в два файла
python MERGED_RUSSIA/migrate_to_two_tables.py

# 3. Загрузить исторические данные в Supabase
python dashboard/upload_to_supabase.py
```

### Ежемесячный мониторинг

```bash
# 1. Парсинг источников (по отдельности)
python LeroyMerlin/LemanaPRO.py
python Obi_selenium/Obi_selenium.py
python Petrovich/Petrovich.py
python KeramogranitRU/KeramogranitRu.py

# 2. Объединение и гармонизация → записывает products.json + prices.json
python MERGED_RUSSIA/Main_scraping_Russia.py

# 3. Загрузка в Supabase
python dashboard/upload_to_supabase.py
```

### Запуск дашборда локально

```bash
# 1. Установить зависимости (один раз)
pip install -r dashboard/requirements.txt

# 2. Создать файл dashboard/.env с ключами Supabase
#    SUPABASE_URL=https://xxx.supabase.co
#    SUPABASE_KEY=your-anon-key

# 3. Запустить
streamlit run dashboard/dashboard.py
```

Дашборд откроется по адресу `http://localhost:8501`

---

## Ключевые решения в коде

### Период данных
`cur_data_file = datetime.now().strftime("%m.%Y")` — определяет, какие JSON-файлы загружать.
Для работы с конкретным месяцем — раскомментировать строку вида `# cur_data_file = "02.2026"`.

### Безопасные преобразования
```python
safe_float(value)  # None / '' → None; убирает пробелы, ₽, %, запятые
safe_int(value)    # аналогично для int
```
Никогда не делать `line.get('field', '').replace(...)` — `get()` может вернуть `None`.
Правильно: `(line.get('field', '') or '').replace(...)`.

### Нормализация формата плитки
- Разделители `×`, `х`, `X` → `x`
- Округление до кратного 5
- Сортировка по убыванию (60x30, не 30x60)
- Словарь `replacements` для нестандартных замен (35x35→30x30, 45x45→50x50, и др.)

### Материалы (только эти три)
`['Керамогранит', 'Керамика', 'Клинкер']` — всё остальное фильтруется.

### Surface finish (surface_finish)
Определяется через `determine_surface_type(type_of_surface, name)`:
- `'Полированный'` / `'Лаппатированный'` / `'Не полированный'`

---

## Модуль harmonization.py (v2.2)

Вызывается из `create_data_card()` для каждой записи:
```python
harmonized = harmonize_record(raw_card)
harmonized['primary_design'] = get_primary_design(harmonized.get('design', ''))
harmonized['primary_color'] = get_primary_color(harmonized.get('color', ''))
```

Что гармонизируется:
- **Единицы измерения** → `м²`, `шт.`, `упаковка`, `комплект`, `коробка`
- **Дизайн** — синонимы объединены, комбинации сохранены (`"Мрамор, Камень"`)
- **Цвет** — оттенки убраны (`"светло-серый"` → `"Серый"`), комбинации сохранены
- **Тип поверхности** → женский род, капитализация (`"матовая"` → `"Матовая"`)
- **Бренды** — суффиксы удалены (`CERAMICA`, `CERAMICHE`, `RUSSIA`, `LIFE` и др.)
- **primary_design** / **primary_color** — первый элемент из комбинации (для фильтрации)

---

## Структура данных (v2)

Два файла вместо единого `data_finally.json`:

| Файл | Назначение | Растёт |
|---|---|---|
| `products.json` | Каталог товаров, статика | Медленно (только новые товары) |
| `prices.json` | История цен/остатков | Каждый мониторинг |

`product_id` = `md5(url)[:16]` — стабильный ID из URL.
`price_id` = `"{product_id}_{date}"` — дедупликационный ключ (один снимок в день).

### Supabase (актуальная схема)

- Таблицы: `products`, `prices`
- Вью: `tiles_v2` — JOIN последних цен к товарам (для дашборда)
- Схема: `dashboard/create_tables_v2.sql`
- Загрузка: upsert по первичному ключу — исторические данные не удаляются
- Батч: 100 записей, порядок загрузки: сначала `products`, потом `prices` (FK)
- Дашборд читает из `tiles_v2`
- Константы: `KERAMIN_BRAND = "КЕРАМИН"`, `STORES_WITH_STOCK = ["LemanaPRO", "OBI", "Petrovich"]`
- `dashboard/.env` содержит `SUPABASE_URL` и `SUPABASE_KEY` — не коммитить

---

## Windows-специфичные проблемы

- **Эмодзи в print()** вызывают `UnicodeEncodeError` — использовать `[+]`, `[!]`, `[OK]`
- JSON-файлы данных в `.gitignore` (не хранятся в репозитории)
- ChromeDriver управляется через `undetected-chromedriver` автоматически

---

## Типичные ошибки

| Ошибка | Решение |
|---|---|
| `AttributeError: 'NoneType' has no attribute 'replace'` | Добавить `or ''` после `line.get(...)` |
| Файл Keramogranit_RU не найден | Имя: `data_MM.YYYY_KeramogranitRu.json` (не `data_finally_...`) |
| Keramogranit_RU с остатками | Остатков нет — три поля должны быть `None` |
| Функция не вызывается в main() | Все 4 функции `get_data_*()` должны быть в `main()` |
| Цена LemanaPRO = None | Считать: `box_price / packaging_m2`, не из поля `Действующая цена` |
