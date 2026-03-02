"""
Загрузка данных из data_finally.json в Supabase.
Запускать после каждого обновления данных (раз в месяц).

Использование:
    python upload_to_supabase.py
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

DATA_PATH = Path(__file__).parent.parent / "MERGED_RUSSIA" / "data_finally.json"
TABLE_NAME = "tiles"
BATCH_SIZE = 100   # Небольшой батч чтобы не таймаутить
MAX_RETRIES = 3


def clean_record(record: dict) -> dict:
    """Убирает пустые строки -> null."""
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, str) and v.strip() == "":
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def insert_batch(client, batch: list, attempt: int = 1):
    try:
        client.table(TABLE_NAME).insert(batch).execute()
    except Exception as e:
        if attempt < MAX_RETRIES:
            print(f"\n[!] Ошибка, повтор {attempt}/{MAX_RETRIES}: {e}")
            time.sleep(2)
            insert_batch(client, batch, attempt + 1)
        else:
            raise


def upload():
    print("[*] Подключение к Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"[*] Загрузка файла: {DATA_PATH}")
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    print(f"[+] Загружено {len(data):,} записей")

    # Очищаем таблицу перед загрузкой (полная перезапись)
    print("[*] Очистка таблицы...")
    client.table(TABLE_NAME).delete().neq("id", 0).execute()
    print("[+] Таблица очищена")

    # Загружаем батчами
    total = len(data)
    uploaded = 0

    for i in range(0, total, BATCH_SIZE):
        batch = [clean_record(r) for r in data[i:i + BATCH_SIZE]]
        insert_batch(client, batch)
        uploaded += len(batch)
        pct = uploaded / total * 100
        print(f"[>] {uploaded:,} / {total:,} ({pct:.1f}%)", end="\r")

    print(f"\n[OK] Загрузка завершена: {uploaded:,} записей в таблице '{TABLE_NAME}'")


if __name__ == "__main__":
    upload()
