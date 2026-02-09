import json
from datetime import datetime
import time
from pathlib import Path
from typing import Dict, Optional
from harmonization import harmonize_record, get_primary_design, get_primary_color

start_time = time.time()

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).parent.parent
MERGED_DIR = BASE_DIR / "MERGED_RUSSIA"

cur_data_file = datetime.now().strftime("%m.%Y")
# cur_data_file = "02.2026"

# Словарь замены нестандартных форматов
replacements = {
    "35x35": "30x30",
    "45x45": "50x50",
    "65x30": "60x30",
    "60x25": "60x30",
    "40x20": "40x25",
    "40x30": "40x25",
    '60x35': '60x30',
    '120x35': '120x30',
    '55x55': '60x60',
    '120x55': '120x50',
    '115x55': '120x60'
}

total_base = []


# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============

def safe_float(value, default=None) -> Optional[float]:
    """Безопасное преобразование в float"""
    if value is None or value == '':
        return default
    try:
        if isinstance(value, str):
            value = value.replace(' ', '').replace(',', '.').replace('₽', '').replace('−', '').replace('%', '').replace('-', '')
        return float(value)
    except (ValueError, AttributeError):
        return default


def safe_int(value, default=None) -> Optional[int]:
    """Безопасное преобразование в int"""
    if value is None or value == '':
        return default
    try:
        if isinstance(value, str):
            value = value.replace(' ', '').replace(',', '.').replace('−', '').replace('%', '').replace('-', '')
        return int(float(value))
    except (ValueError, AttributeError):
        return default


def calculate_price_range(price: Optional[float]) -> Optional[str]:
    """Расчет диапазона цены"""
    if price is None:
        return None
    try:
        lower = (round(price // 100) * 100)
        upper = lower + 100
        return f'{lower}-{upper}'
    except:
        return None


def calculate_sale_range(sale: Optional[float]) -> Optional[str]:
    """Расчет диапазона скидки"""
    if sale is None:
        return None
    try:
        lower = (round(sale // 10) * 10)
        upper = lower + 10
        return f'{lower}-{upper}'
    except:
        return None


def normalize_format(original_format: Optional[str]) -> Optional[str]:
    """Нормализация формата плитки"""
    if not original_format:
        return None
    try:
        # Заменяем различные разделители на 'x'
        original_format = original_format.replace('×', 'x').replace('х', 'x').replace('X', 'x')

        list_of_sizes = original_format.split('x')
        # Округляем до ближайшего значения кратного 5
        float_list_of_sizes = [round(float(x) / 5) * 5 for x in list_of_sizes]
        # Сортируем по убыванию
        format_str = 'x'.join(map(str, sorted(float_list_of_sizes, reverse=True)))
        # Применяем замены нестандартных форматов
        return replacements.get(format_str, format_str)
    except:
        return None


def determine_surface_type(type_of_surface: str, name: str) -> str:
    """Определение типа покрытия поверхности"""
    if not type_of_surface and not name:
        return "Не полированный"

    type_lower = type_of_surface.lower() if type_of_surface else ''
    name_lower = name.lower() if name else ''

    if 'полирован' in type_lower or 'полирован' in name_lower:
        return 'Полированный'
    elif 'лаппатирован' in type_lower or 'лаппатирован' in name_lower:
        return 'Лаппатированный'
    else:
        return "Не полированный"


def determine_material(name: str, material_field: str = '') -> Optional[str]:
    """Определение материала плитки"""
    name_lower = name.lower() if name else ''
    material_lower = material_field.lower() if material_field else ''

    if 'линкер' in name_lower or 'клинкер' in material_lower:
        return 'Клинкер'
    elif 'керамогранит' in name_lower or 'напольная' in name_lower or 'керамогранит' in material_lower:
        return 'Керамогранит'
    elif 'керамик' in material_lower or 'глина' in material_lower or 'плитка' in name_lower:
        return 'Керамика'

    return material_field if material_field else None


def process_availability_lemana(availability: str, online_order: str) -> str:
    """
    Обработка поля 'В наличии' для LemanaPRO

    Логика:
    - Если товар не в наличии -> "Нет в наличии"
    - Если товар доступен только при онлайн-заказе -> "Онлайн-заказ LemanaPRO"
    - Если товар доступен в магазинах -> "Доступен в магазинах LemanaPRO"
    """
    if not availability or availability.lower() in ['нет в наличии', 'отсутствует', 'недоступен']:
        return "Нет в наличии"

    if online_order and 'только онлайн' in online_order.lower():
        return "Онлайн-заказ LemanaPRO"

    if 'в наличии' in availability.lower():
        return "Доступен в магазинах LemanaPRO"

    return availability


def create_data_card(line: Dict, store: str) -> Dict:
    """
    Создание финальной карточки товара в едином формате
    Применяет гармонизацию данных для приведения к единому стилю
    """
    raw_card = {
        'Полное Наименование': line.get('name', ''),
        'Действующая цена': line.get('price'),
        "Диапазон действующей цены": line.get('price_range'),
        "Размер скидки": line.get('sale'),
        "Диапазон размера скидки": line.get('sale_range'),
        'Единица измерения цены': line.get('mesure', ''),
        'Ссылка': line.get('link', ''),
        'Магазин': store,
        'Наличие': line.get('availability', ''),
        'Дата мониторинга': line.get('date_scrap', ''),
        'Время мониторинга': line.get('time_scrap', ''),
        'Цвет': line.get('colour', ''),
        'Коллекция': line.get('collection', ''),
        'Бренд': line.get('brand', ''),
        'Страна': line.get('country', ''),
        'Бренд-Страна': line.get('brand_country', ''),
        'Толщина': line.get('thickness'),
        'Оригинальный формат': line.get('original_format', ''),
        'Формат': line.get('format'),
        'Дизайн': line.get('design', ''),
        'Материал': line.get('material', ''),
        'Тип поверхности': line.get('type_of_surface', ''),
        'Тип покрытия (полир/лапп/неполир)': line.get('surface', ''),
        'Структура': line.get('structure', ''),
        "Количество лиц": line.get('number_of_pictures', ''),
        'Общий остаток': line.get('total_base_stock', ''),
        'Упаковка': line.get('packaging'),
        'Общий остаток в единицах измерения': line.get('total_stock')
    }

    # Применяем гармонизацию данных
    harmonized = harmonize_record(raw_card)

    # Добавляем поля с основными (первыми) значениями для комбинаций
    harmonized['Основной дизайн'] = get_primary_design(harmonized.get('Дизайн', ''))
    harmonized['Основной цвет'] = get_primary_color(harmonized.get('Цвет', ''))

    return harmonized


# ============= ФУНКЦИИ ЗАГРУЗКИ ДАННЫХ =============

def get_data_LemanaPRO():
    """Загрузка и обработка данных LemanaPRO"""
    file_path = BASE_DIR / 'LeroyMerlin' / f'data_{cur_data_file}_Tiles_LemanaPRO.json'

    if not file_path.exists():
        print(f"[!] Файл не найден: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[+] LemanaPRO: Загружено {len(data)} записей")
    processed = 0

    for line in data:
        name = line.get('Полное наименование', '')

        # Определение материала
        material = line.get("Основной материал", '')
        material = determine_material(name, material)

        if material == 'Белая глина':
            material = 'Керамика'

        # Фильтруем только нужные материалы
        if material not in ['Керамогранит', 'Керамика', 'Клинкер']:
            continue

        # Цена и скидка
        # ВАЖНО: В исходных данных LemanaPRO "Действующая цена" = null
        # Нужно вычислить цену за м² из "Цены за коробку" и "Упаковки (м²)"
        price = None
        packaging_m2 = safe_float(line.get('Упаковка (м²)', ''))
        box_price_str = line.get('Цена за коробку', '')

        if box_price_str and packaging_m2 and packaging_m2 > 0:
            # Очищаем строку цены от пробелов и других символов
            box_price_clean = box_price_str.replace(' ', '').replace('\xa0', '').replace(',', '.')
            box_price = safe_float(box_price_clean)

            if box_price:
                # Вычисляем цену за м²
                price = round(box_price / packaging_m2, 2)

        price_range = calculate_price_range(price)

        sale = safe_int(line.get('Скидка', ''))
        sale_range = calculate_sale_range(sale)

        # Обработка наличия (реализация комментария строки 129)
        availability_raw = line.get("В наличии", '')
        online_order = line.get("Онлайн заказ", '')
        availability = process_availability_lemana(availability_raw, online_order)

        # Цвет
        colour = line.get("Цвет", '')
        if not colour:
            colour = line.get("Цветовая палитра", '')
        if colour and '/' in colour:
            colour = colour.split('/')[0].strip()

        # Бренд и страна
        brand = line.get("Бренд", '').upper()
        country = line.get("Страна производства", '').upper()
        brand_country = f'{brand} ({country})' if brand and country else brand or country

        # Толщина
        thickness = safe_float(line.get("Толщина (мм)", ''))

        # Поверхность
        type_of_surface = line.get("Внешний вид поверхности", '')
        surface = determine_surface_type(type_of_surface, name)

        # Формат
        original_format = line.get('Габариты (ШхД)', '').replace('×', 'x')
        format_normalized = normalize_format(original_format)

        # Единица измерения
        # ВАЖНО: В исходных данных "Единица измерения цены" = null
        # Определяем на основе других полей
        mesure = ''
        if packaging_m2 and packaging_m2 > 0:
            # Если есть упаковка в м², значит цена за м²
            mesure = 'м²'
        elif line.get('Единица хранения на складе') == 'шт.':
            # Если хранится в штуках, значит цена за штуку
            mesure = 'шт.'
        else:
            # По умолчанию для плитки - м²
            mesure = 'м²'

        # Остатки и упаковка
        total_base_stock = safe_float(line.get('Общий остаток', ''))
        packaging = packaging_m2

        total_stock = None
        if total_base_stock is not None and packaging is not None:
            total_stock = round(total_base_stock * packaging)

        # Создаем промежуточный словарь
        processed_line = {
            'name': name,
            'price': price,
            'price_range': price_range,
            'sale': sale,
            'sale_range': sale_range,
            'mesure': mesure,
            'link': line.get("Ссылка", ''),
            'availability': availability,
            'date_scrap': line.get("Дата мониторинга", ''),
            'time_scrap': line.get("Время мониторинга", ''),
            'colour': colour,
            'collection': line.get("Коллекция", ''),
            'brand': brand,
            'country': country,
            'brand_country': brand_country,
            'thickness': thickness,
            'original_format': original_format,
            'format': format_normalized,
            'design': line.get("Эффект", ''),
            'material': material,
            'type_of_surface': type_of_surface,
            'surface': surface,
            'structure': line.get('Поверхность', ''),
            'number_of_pictures': line.get('Количество различных рисунков', ''),
            'total_base_stock': total_base_stock,
            'packaging': packaging,
            'total_stock': total_stock
        }

        total_base.append(create_data_card(processed_line, 'LemanaPRO'))
        processed += 1

    print(f"    Обработано {processed} записей")


def get_data_OBI():
    """Загрузка и обработка данных OBI"""
    file_path = BASE_DIR / 'Obi_selenium' / f'data_{cur_data_file}_plitka_plitka_i_keramogranit_Москва_obi.json'

    if not file_path.exists():
        print(f"[!] Файл не найден: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[+] OBI: Загружено {len(data)} записей")
    processed = 0

    for line in data:
        name = line.get('Наименование товара', '')
        if not name:
            continue

        # Определение материала
        material = line.get("Материал", '')
        material = determine_material(name, material)

        # Фильтрация
        if material not in ['Керамогранит', 'Клинкер', 'Керамика']:
            continue
        if any(word in name for word in ['Гипс', 'Бетонная', 'фасадная']):
            continue

        # Цена и скидка
        price = safe_float(line.get('Действующая цена', ''))
        mesure = line.get("Единица измерения цены", '').replace('за М²', 'м²')
        price_range = calculate_price_range(price)

        sale = safe_float(line.get('Размер скидки', ''))
        sale_range = calculate_sale_range(sale)

        # Бренд и страна
        brand = line.get("Бренд", '').upper()
        country = line.get("Страна производства", '').replace('Республика ', '').upper()
        brand_country = f'{brand} ({country})' if brand and country else brand or country

        # Толщина
        thickness = safe_float(line.get("Толщина", '').replace(' мм', ''))

        # Поверхность
        type_of_surface = line.get("Поверхность", '')
        surface = determine_surface_type(type_of_surface, name)

        # Структура
        structure = 'Структурированная' if 'структуриров' in name.lower() or type_of_surface == 'Структурированная' else 'Гладкая'

        # Формат
        original_format = None
        try:
            length = safe_float(line.get('Длина', '').replace(' см', ''))
            width = safe_float(line.get('Ширина', '').replace(' см', ''))
            if length and width:
                original_format = f"{max(length, width)}x{min(length, width)}"
        except:
            # Пытаемся извлечь из названия
            try:
                name_parts = name.split()
                if "см" in name_parts:
                    idx = name_parts.index("см") - 1
                    size_str = name_parts[idx].replace('X', 'x').replace(',', '.')
                    parts = [float(x) for x in size_str.split('x')]
                    original_format = f'{max(parts)}x{min(parts)}'
            except:
                pass

        format_normalized = normalize_format(original_format)

        # Остатки и упаковка
        total_base_stock = safe_float(line.get('Общий остаток', ''))

        packaging = None
        try:
            name_list = name.split()
            if name_list[-1] == 'м²':
                packaging = safe_float(name_list[-2])
            elif 'шт' not in mesure:
                square = safe_float(line.get('Площадь элемента', '').replace(' м²', ''))
                qty_in_pack = safe_int(line.get('Количество в упаковке', '').replace(' шт', ''))
                if square and square > 1:
                    packaging = square
                elif square and qty_in_pack:
                    packaging = round(square * qty_in_pack, 3)
        except:
            pass

        total_stock = None
        if total_base_stock is not None and packaging is not None:
            total_stock = round(total_base_stock * packaging)

        # Создаем промежуточный словарь
        processed_line = {
            'name': name,
            'price': price,
            'price_range': price_range,
            'sale': sale,
            'sale_range': sale_range,
            'mesure': mesure,
            'link': line.get("Ссылка", ''),
            'availability': line.get("В наличии", ''),
            'date_scrap': line.get("Дата мониторинга", ''),
            'time_scrap': line.get("Время мониторинга", ''),
            'colour': line.get("Основной цвет", ''),
            'collection': line.get("Серия / Коллекция", ''),
            'brand': brand,
            'country': country,
            'brand_country': brand_country,
            'thickness': thickness,
            'original_format': original_format,
            'format': format_normalized,
            'design': line.get("Имитация материала", ''),
            'material': material,
            'type_of_surface': type_of_surface,
            'surface': surface,
            'structure': structure,
            'number_of_pictures': 'Не указано',
            'total_base_stock': total_base_stock,
            'packaging': packaging,
            'total_stock': total_stock
        }

        total_base.append(create_data_card(processed_line, 'OBI'))
        processed += 1

    print(f"    Обработано {processed} записей")


def get_data_Petrovich():
    """Загрузка и обработка данных Petrovich"""
    file_path = BASE_DIR / 'Petrovich' / f'data_{cur_data_file}_plitka_Petrovich.json'

    if not file_path.exists():
        print(f"[!] Файл не найден: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[+] Petrovich: Загружено {len(data)} записей")
    processed = 0

    for line in data:
        # Фильтрация вспомогательных товаров
        if line.get('Тип товара', '') in ['Заглушка', 'Затирка', 'Клинья', 'Крестики для плитки',
                                          'Очиститель', 'Профиль', 'Система выравнивания плитки', 'Уголок']:
            continue

        name = line.get('Полное наименование', '')

        # Определение материала
        material = line.get("Материал", '')
        if material == 'Керамическая плитка':
            material = 'Керамика'
        material = determine_material(name, material)

        # Цена и скидка
        price = safe_float(line.get('Действующая цена', ''))
        mesure = line.get("Единица измерения цены", '').replace('м2', 'м²')
        price_range = calculate_price_range(price)

        # Расчет скидки
        old_price = safe_float(line.get('Цена без скидки', ''))
        sale = None
        if price and old_price and old_price > price:
            sale = round((1 - price / old_price) * 100)
        sale_range = calculate_sale_range(sale)

        # Бренд и страна
        brand = line.get("Бренд", '').upper()
        country = line.get("Страна-производитель", '').upper()
        brand_country = f'{brand} ({country})' if brand and country else brand or country

        # Толщина
        thickness = safe_float(line.get("Толщина, мм", ''))

        # Поверхность
        type_of_surface = line.get("Поверхность", '')
        surface = determine_surface_type(type_of_surface, name)

        # Формат
        original_format = None
        try:
            length_mm = safe_float(line.get('Длина, мм', ''))
            width_mm = safe_float(line.get('Ширина, мм', ''))
            if length_mm and width_mm:
                length_cm = length_mm / 10
                width_cm = width_mm / 10
                original_format = f"{max(length_cm, width_cm)}x{min(length_cm, width_cm)}"
        except:
            pass

        # Если не получилось из отдельных полей, пробуем поле "Размеры, мм"
        if not original_format:
            try:
                size_str = line.get('Размеры, мм', '')
                if size_str:
                    # Заменяем различные варианты разделителей на 'x'
                    size_clean = size_str.replace('х', 'x').replace('Х', 'x').replace('X', 'x').replace('×', 'x').replace('�', 'x')

                    # Разделяем по 'x' и берем только первые 2 размера (игнорируем толщину)
                    parts = size_clean.split('x')
                    if len(parts) >= 2:
                        length = float(parts[0])
                        width = float(parts[1])

                        # Формат в мм, конвертируем в см: большее x меньшее
                        original_format = f"{max(length, width) / 10}x{min(length, width) / 10}"
            except:
                pass

        format_normalized = normalize_format(original_format)

        # Остатки и упаковка
        total_base_stock = safe_float(line.get('Общий остаток', ''))
        packaging_str = line.get('Продается коробками по', '') or ''
        packaging = safe_float(packaging_str.replace('1 упак = ', '').replace(' м2', ''))

        total_stock = None
        if total_base_stock is not None and packaging is not None:
            total_stock = round(total_base_stock * packaging)

        # Создаем промежуточный словарь
        processed_line = {
            'name': name,
            'price': price,
            'price_range': price_range,
            'sale': sale,
            'sale_range': sale_range,
            'mesure': mesure,
            'link': line.get("Ссылка", ''),
            'availability': 'В наличии',
            'date_scrap': line.get("Дата мониторинга", ''),
            'time_scrap': line.get("Время мониторинга", ''),
            'colour': line.get("Цвет", ''),
            'collection': line.get("Коллекция", ''),
            'brand': brand,
            'country': country,
            'brand_country': brand_country,
            'thickness': thickness,
            'original_format': original_format,
            'format': format_normalized,
            'design': line.get("Дизайн", ''),
            'material': material,
            'type_of_surface': type_of_surface,
            'surface': surface,
            'structure': line.get('Фактура', ''),
            'number_of_pictures': line.get('Количество лиц', ''),
            'total_base_stock': total_base_stock,
            'packaging': packaging,
            'total_stock': total_stock
        }

        total_base.append(create_data_card(processed_line, 'Petrovich'))
        processed += 1

    print(f"    Обработано {processed} записей")


def get_data_keramogranit_ru():
    """Загрузка и обработка данных Keramogranit_RU"""
    file_path = BASE_DIR / 'KeramogranitRU' / f'data_{cur_data_file}_KeramogranitRu.json'

    if not file_path.exists():
        print(f"[!] Файл не найден: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[+] Keramogranit_RU: Загружено {len(data)} записей")
    processed = 0

    for line in data:
        # Фильтрация по типу плитки и единице измерения
        type_plitka = line.get('Тип плитки', '')
        mesure = line.get('Единица измерения цены', '').replace('м2', 'м²')

        if type_plitka not in ['универсальная плитка', 'для стен', 'для пола'] and 'руб./м2' not in mesure:
            continue

        name = line.get('Полное наименование', '')

        # Определение материала
        material = determine_material(name, '')
        if type_plitka in ['универсальная плитка', 'для пола']:
            material = 'Керамогранит'
        elif not material:
            material = 'Керамика'

        # Цена и скидка
        price = safe_float(line.get('Действующая цена', ''))
        price_range = calculate_price_range(price)

        old_price = safe_float(line.get('Цена без скидки', ''))
        sale = None
        if price and old_price and old_price > price:
            sale = round((1 - price / old_price) * 100)
        sale_range = calculate_sale_range(sale)

        # Бренд и страна
        producer = line.get("Производитель", '').upper()
        brand = producer.split('(')[0].strip() if '(' in producer else producer
        country = line.get("Страна", '').upper()
        brand_country = producer if producer else f'{brand} ({country})'

        # Толщина
        thickness = safe_float(line.get("Толщина, мм", ''))

        # Поверхность
        type_of_surface = line.get("Поверхность", '')
        surface = determine_surface_type(type_of_surface, name)

        # Формат
        # Для Keramogranit_RU основной источник - поле "Размер"
        # Формат уже в сантиметрах, может содержать толщину (30x60x9)
        original_format = None
        size_from_field = line.get('Размер', '')

        if size_from_field:
            try:
                # Заменяем различные варианты разделителей на 'x'
                size_clean = size_from_field.replace('х', 'x').replace('Х', 'x').replace('X', 'x').replace('×', 'x')

                # Разделяем по 'x' и берем только первые 2 размера (игнорируем толщину)
                parts = size_clean.split('x')
                if len(parts) >= 2:
                    # Берем только длину и ширину, игнорируем толщину
                    length = float(parts[0])
                    width = float(parts[1])

                    # Формат: большее x меньшее
                    original_format = f"{max(length, width)}x{min(length, width)}"
            except:
                pass

        format_normalized = normalize_format(original_format)

        # ВАЖНО: У Keramogranit_RU НЕТ остатков
        # Поэтому оставляем эти поля пустыми

        # Создаем промежуточный словарь
        processed_line = {
            'name': name,
            'price': price,
            'price_range': price_range,
            'sale': sale,
            'sale_range': sale_range,
            'mesure': mesure,
            'link': line.get("Ссылка", ''),
            'availability': line.get("В наличии", ''),
            'date_scrap': line.get("Дата мониторинга", ''),
            'time_scrap': line.get("Время мониторинга", ''),
            'colour': line.get("Цвет", ''),
            'collection': line.get("Коллекция", ''),
            'brand': brand,
            'country': country,
            'brand_country': brand_country,
            'thickness': thickness,
            'original_format': original_format,
            'format': format_normalized,
            'design': line.get("Рисунок поверхности", ''),
            'material': material,
            'type_of_surface': type_of_surface,
            'surface': surface,
            'structure': line.get('Фактура', ''),
            'number_of_pictures': line.get('Количество лиц', ''),
            'total_base_stock': None,  # Нет остатков
            'packaging': None,  # Нет остатков
            'total_stock': None  # Нет остатков
        }

        total_base.append(create_data_card(processed_line, 'Keramogranit_ru'))
        processed += 1

    print(f"    Обработано {processed} записей")


# ============= ФУНКЦИИ РАБОТЫ С ФАЙЛАМИ =============

def append_data():
    """Добавление данных в финальный файл"""
    output_file = MERGED_DIR / 'data_finally.json'

    if not output_file.exists():
        print(f"\n[*] Создаю новый файл: data_finally.json")
        existing_data = []
    else:
        try:
            with open(output_file, 'r', encoding='utf-8') as file:
                existing_data = json.load(file)
        except json.JSONDecodeError:
            print(f"[!] Файл data_finally.json поврежден. Создаю новый...")
            existing_data = []

    existing_data.extend(total_base)

    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)

    print(f"\n[OK] Добавлено {len(total_base)} объектов. Всего в файле: {len(existing_data)} объектов")


def remove_full_duplicates(filename='data_finally.json'):
    """Удаление полных дубликатов"""
    file_path = MERGED_DIR / filename

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        unique_data = []
        seen = set()

        for item in data:
            item_tuple = tuple(sorted(item.items()))
            if item_tuple not in seen:
                seen.add(item_tuple)
                unique_data.append(item)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(unique_data, file, ensure_ascii=False, indent=4)

        removed = len(data) - len(unique_data)
        print(f"[-] Удалено {removed} полных дубликатов. Осталось {len(unique_data)} записей.")

    except FileNotFoundError:
        print(f"[!] Файл {filename} не найден.")
    except json.JSONDecodeError:
        print(f"[!] Ошибка чтения файла {filename}")


# ============= ГЛАВНАЯ ФУНКЦИЯ =============

def main():
    """Главная функция запуска обработки всех источников"""
    print("=" * 60)
    print("НАЧАЛО ОБРАБОТКИ ДАННЫХ")
    print(f"Период данных: {cur_data_file}")
    print("=" * 60)

    # Загрузка данных из всех источников
    get_data_LemanaPRO()
    get_data_OBI()
    get_data_Petrovich()
    get_data_keramogranit_ru()  # ИСПРАВЛЕНО: добавлен вызов функции

    print("\n" + "=" * 60)
    print(f"ИТОГО обработано: {len(total_base)} записей")
    print("=" * 60)

    # Сохранение данных
    append_data()
    remove_full_duplicates()

    print("\n[OK] ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")


if __name__ == '__main__':
    main()
    finish_time = round(time.time() - start_time, 1)
    print(f"\nВремя выполнения: {finish_time} секунд")
