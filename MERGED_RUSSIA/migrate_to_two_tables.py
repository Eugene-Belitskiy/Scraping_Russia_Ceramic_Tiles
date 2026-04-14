"""
Одноразовый скрипт миграции: data_finally.json -> products.json + prices.json

Запускать ОДИН РАЗ перед следующим циклом мониторинга.
Если products.json или prices.json уже существуют — скрипт остановится.

Использование:
    python MERGED_RUSSIA/migrate_to_two_tables.py
"""

import json
import hashlib
from pathlib import Path

MERGED_DIR = Path(__file__).parent


def make_product_id(url: str) -> str:
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]


def migrate():
    src = MERGED_DIR / 'data_finally.json'
    dst_products = MERGED_DIR / 'products.json'
    dst_prices = MERGED_DIR / 'prices.json'

    # Защита от повторного запуска
    if dst_products.exists() or dst_prices.exists():
        print("[!] products.json или prices.json уже существуют. Миграция отменена.")
        print("    Удалите эти файлы вручную, если хотите запустить миграцию заново.")
        return

    if not src.exists():
        print(f"[!] Файл {src} не найден. Нечего мигрировать.")
        return

    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    print(f"[+] Загружено {len(data):,} записей из data_finally.json")

    products = []
    prices = []
    seen_ids = set()
    no_url_count = 0

    for record in data:
        url = record.get('url', '')
        if not url:
            no_url_count += 1
            continue

        pid = make_product_id(url)
        date = record.get('date', '')

        product = {
            'product_id':      pid,
            'date_added':      date,
            'url':             url,
            'store':           record.get('store', ''),
            'name':            record.get('name', ''),
            'color':           record.get('color', ''),
            'primary_color':   record.get('primary_color', ''),
            'collection':      record.get('collection', ''),
            'brand':           record.get('brand', ''),
            'country':         record.get('country', ''),
            'brand_country':   record.get('brand_country', ''),
            'thickness':       record.get('thickness'),
            'original_format': record.get('original_format', ''),
            'format':          record.get('format'),
            'design':          record.get('design', ''),
            'primary_design':  record.get('primary_design', ''),
            'material':        record.get('material', ''),
            'surface_type':    record.get('surface_type', ''),
            'surface_finish':  record.get('surface_finish', ''),
            'structure':       record.get('structure', ''),
            'patterns_count':  record.get('patterns_count', ''),
            'package_size':    record.get('package_size'),
            'price_unit':      record.get('price_unit', ''),
        }

        price = {
            'price_id':          f"{pid}_{date}",
            'product_id':        pid,
            'store':             record.get('store', ''),
            'date':              date,
            'time':              record.get('time', ''),
            'price':             record.get('price'),
            'price_range':       record.get('price_range'),
            'discount':          record.get('discount'),
            'discount_range':    record.get('discount_range'),
            'availability':      record.get('availability', ''),
            'total_stock':       record.get('total_stock'),
            'total_stock_units': record.get('total_stock_units'),
        }

        # Добавляем товар только один раз (дедупликация по product_id)
        if pid not in seen_ids:
            products.append(product)
            seen_ids.add(pid)

        prices.append(price)

    # Запись результатов
    dst_products.write_text(
        json.dumps(products, ensure_ascii=False, indent=4), encoding='utf-8')
    dst_prices.write_text(
        json.dumps(prices, ensure_ascii=False, indent=4), encoding='utf-8')

    print(f"\n[OK] products.json: {len(products):,} уникальных товаров")
    print(f"[OK] prices.json:   {len(prices):,} записей цен")

    if no_url_count:
        print(f"[!] Пропущено {no_url_count} записей без URL")

    # Проверка целостности
    duplicates = len(data) - no_url_count - len(products)
    if duplicates > 0:
        print(f"[*] Обнаружено {duplicates} дублирующихся товаров (один URL — одна карточка)")

    print("\n[OK] МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    print("     Теперь можно применить create_tables_v2.sql в Supabase")
    print("     и запустить обновлённый upload_to_supabase.py")


if __name__ == '__main__':
    migrate()
