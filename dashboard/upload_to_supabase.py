"""
Загрузка данных из products.json и prices.json в Supabase.
Запускать после каждого обновления данных (раз в месяц).

Стратегия загрузки:
- products: upsert по product_id — никогда не удаляет исторические данные
- prices:   upsert по price_id   — идемпотентно, безопасно перезапускать

ВАЖНО: сначала загружаются products, потом prices (из-за внешнего ключа).

Использование:
    python dashboard/upload_to_supabase.py
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Загрузка .env
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

MERGED_DIR     = Path(__file__).parent.parent / "MERGED_RUSSIA"
PRODUCTS_PATH  = MERGED_DIR / "products.json"
PRICES_PATH    = MERGED_DIR / "prices.json"
PRODUCTS_TABLE = "products"
PRICES_TABLE   = "prices"
BATCH_SIZE     = 100   # Небольшой батч чтобы не таймаутить
MAX_RETRIES    = 3


def clean_record(record: dict) -> dict:
    """Заменяет пустые строки на null для корректной записи в Supabase."""
    return {
        k: (None if isinstance(v, str) and v.strip() == "" else v)
        for k, v in record.items()
    }


def upsert_batch(client, table: str, batch: list, attempt: int = 1):
    try:
        client.table(table).upsert(batch).execute()
    except Exception as e:
        if attempt < MAX_RETRIES:
            print(f"\n[!] Ошибка {table}, повтор {attempt}/{MAX_RETRIES}: {e}")
            time.sleep(2)
            upsert_batch(client, table, batch, attempt + 1)
        else:
            raise


def upload_table(client, table_name: str, data_path: Path):
    """Загружает все записи из JSON-файла в таблицу Supabase через upsert."""
    if not data_path.exists():
        print(f"[!] Файл не найден: {data_path} — пропускаю")
        return

    print(f"\n[*] Загрузка: {data_path.name} -> таблица '{table_name}'")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    total = len(data)
    print(f"[+] Записей в файле: {total:,}")

    uploaded = 0
    for i in range(0, total, BATCH_SIZE):
        batch = [clean_record(r) for r in data[i:i + BATCH_SIZE]]
        upsert_batch(client, table_name, batch)
        uploaded += len(batch)
        pct = uploaded / total * 100
        print(f"[>] {uploaded:,} / {total:,} ({pct:.1f}%)", end="\r")

    print(f"\n[OK] {table_name}: {uploaded:,} записей загружено (upsert)")


def upload():
    print("[*] Подключение к Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # products загружаем первыми (prices имеет FK на products)
    upload_table(client, PRODUCTS_TABLE, PRODUCTS_PATH)
    upload_table(client, PRICES_TABLE, PRICES_PATH)

    print("\n[OK] ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО!")


if __name__ == "__main__":
    upload()
