"""
Модуль гармонизации данных для проекта Scraping_Russia
Приводит различные вариации значений полей к единому стандарту
"""
import re
from typing import Optional, Union


# ============= ГАРМОНИЗАЦИЯ ЕДИНИЦ ИЗМЕРЕНИЯ =============

def harmonize_measurement_unit(value: str) -> str:
    """
    Гармонизация единиц измерения цены

    Приводит к стандарту: "м²", "шт.", "упаковка", "комплект", "коробка"
    """
    if not value:
        return ''

    value = value.strip().lower()

    # м² (квадратные метры)
    if any(x in value for x in ['м²', 'м2', 'кв.м', '/м²', '/м2']):
        return 'м²'

    # Штука
    if any(x in value for x in ['шт', 'штук']):
        return 'шт.'

    # Упаковка
    if 'упаковк' in value:
        return 'упаковка'

    # Комплект
    if 'комплект' in value:
        return 'комплект'

    # Коробка
    if 'кор' in value:
        return 'коробка'

    return value


# ============= ГАРМОНИЗАЦИЯ ДИЗАЙНА =============

def harmonize_design(value: str) -> str:
    """
    Гармонизация дизайна плитки

    Правила:
    1. СОХРАНЯЕТ комбинированные дизайны (через запятую)
    2. Гармонизирует каждую часть отдельно
    3. Убирает "под " в начале каждой части
    4. Приводит к верхнему регистру первую букву
    5. Объединяет синонимы
    """
    if not value:
        return ''

    value = value.strip()

    # Обработка пустых или бессмысленных значений
    if value.lower() in ['товар без эффекта', 'без эффекта', '']:
        return 'Моноколор'

    # Словарь синонимов и замен
    design_mapping = {
        'мрамор': 'Мрамор',
        'камень': 'Камень',
        'бетон': 'Бетон',
        'цемент': 'Бетон',  # Цемент = Бетон
        'дерево': 'Дерево',
        'паркет': 'Дерево',  # Паркет = Дерево
        'моноколор': 'Моноколор',
        'терраццо': 'Терраццо',
        'оникс': 'Оникс',
        'металл': 'Металл',
        'мозаику': 'Мозаика',
        'мозаика': 'Мозаика',
        'травертин': 'Травертин',
        'рисунком': 'С рисунком',
        'пэчворк': 'Пэчворк',
        'состаренная': 'Рустик',
        'рустик': 'Рустик',
        'песок': 'Песок',
        'листьями': 'Растительный',
        'полоску': 'Полоска',
        'ткань': 'Ткань',
        'кирпич': 'Кирпич',
        'штукатурка': 'Штукатурка'
    }

    def harmonize_single_design(part: str) -> str:
        """Гармонизирует одну часть дизайна"""
        part = part.strip()
        if not part:
            return ''

        # Убираем "под "
        part = part.replace('под ', '').replace('Под ', '')

        # Проверяем в словаре синонимов
        part_lower = part.lower().strip()
        for key, standard in design_mapping.items():
            if key in part_lower:
                return standard

        # Если не нашли в словаре, капитализируем первую букву
        return part.capitalize()

    # Если есть комбинированные дизайны через запятую
    if ',' in value:
        parts = [p.strip() for p in value.split(',')]
        harmonized_parts = []
        seen = set()  # Для удаления дубликатов

        for part in parts:
            harmonized = harmonize_single_design(part)
            if harmonized and harmonized not in seen:
                seen.add(harmonized)
                harmonized_parts.append(harmonized)

        # Объединяем обратно через запятую
        return ', '.join(harmonized_parts) if harmonized_parts else 'Моноколор'
    else:
        # Одиночный дизайн
        return harmonize_single_design(value)


# ============= ГАРМОНИЗАЦИЯ ТИПА ПОВЕРХНОСТИ =============

def harmonize_surface_type(value: str) -> str:
    """
    Гармонизация типа поверхности

    Приводит к стандарту в женском роде:
    "Матовая", "Полированная", "Глянцевая", "Лаппатированная", "Структурированная", и т.д.
    """
    if not value:
        return ''

    value = value.strip().lower()

    # Убираем сложные комбинации, берем основное
    if ',' in value:
        parts = [p.strip() for p in value.split(',')]
        # Приоритет: полированная > лаппатированная > глянцевая > матовая
        priority = ['полирован', 'лаппатирован', 'глянцев', 'матов']
        for prior in priority:
            for part in parts:
                if prior in part:
                    value = part
                    break

    # Убираем дополнительные описания в скобках
    if '(' in value:
        value = value.split('(')[0].strip()

    # Основные типы
    if 'полирован' in value:
        return 'Полированная'
    elif 'лаппатирован' in value or 'полуполир' in value:
        return 'Лаппатированная'
    elif 'глянцев' in value:
        return 'Глянцевая'
    elif 'полуматов' in value:
        return 'Полуматовая'
    elif 'матов' in value:
        return 'Матовая'
    elif 'структур' in value or 'рельеф' in value:
        return 'Структурированная'
    elif 'сатин' in value:
        return 'Сатинированная'
    elif 'карвинг' in value:
        return 'Карвинг'
    elif '3d' in value or 'объем' in value:
        return '3D / Объемная'
    elif 'гладк' in value:
        return 'Гладкая'
    elif 'неполирован' in value:
        return 'Неполированная'
    elif 'шероховат' in value:
        return 'Шероховатая'
    elif 'противоскольз' in value or 'антислип' in value:
        return 'Противоскользящая'

    # По умолчанию - капитализируем
    return value.capitalize()


# ============= ГАРМОНИЗАЦИЯ ЦВЕТА =============

def harmonize_color(value: str) -> str:
    """
    Гармонизация цвета плитки

    Правила:
    1. СОХРАНЯЕТ комбинированные цвета (через запятую, слэш, точку с запятой)
    2. Убирает оттенки типа "светло-", "темно-", "ярко-"
    3. Приводит к единому написанию (первая буква заглавная, остальные строчные)
    4. Объединяет синонимы
    """
    if not value:
        return ''

    value = value.strip()

    # Словарь синонимов цветов
    color_mapping = {
        'бежевый': 'Бежевый',
        'беж': 'Бежевый',
        'белый': 'Белый',
        'серый': 'Серый',
        'сірий': 'Серый',  # опечатка
        'коричневый': 'Коричневый',
        'черный': 'Черный',
        'зеленый': 'Зеленый',
        'синий': 'Синий',
        'голубой': 'Голубой',
        'красный': 'Красный',
        'желтый': 'Желтый',
        'оранжевый': 'Оранжевый',
        'розовый': 'Розовый',
        'фиолетовый': 'Фиолетовый',
        'бордовый': 'Бордовый',
        'кремовый': 'Кремовый',
        'слоновая кость': 'Слоновая кость',
        'терракотовый': 'Терракотовый',
        'терракота': 'Терракотовый',
        'песочный': 'Песочный',
        'горчичный': 'Горчичный',
        'мятный': 'Мятный',
        'бирюзовый': 'Бирюзовый',
        'лазурный': 'Голубой',  # синоним
        'графитовый': 'Серый',  # темно-серый
        'графит': 'Серый',
        'антрацит': 'Серый',
        'жемчужный': 'Белый',  # светлый оттенок
        'молочный': 'Белый'
    }

    def harmonize_single_color(part: str) -> str:
        """Гармонизирует один цвет"""
        part = part.strip().lower()
        if not part:
            return ''

        # Убираем оттенки
        prefixes_to_remove = [
            'светло-', 'светло ', 'светлый ',
            'темно-', 'темно ', 'темный ',
            'ярко-', 'ярко ', 'яркий ',
            'бледно-', 'бледно ', 'бледный ',
            'насыщенный ', 'глубокий '
        ]

        for prefix in prefixes_to_remove:
            if part.startswith(prefix):
                part = part[len(prefix):].strip()
                break

        # Проверяем в словаре синонимов
        for key, standard in color_mapping.items():
            if part == key or part.startswith(key):
                return standard

        # Если не нашли в словаре, капитализируем
        return part.capitalize()

    # Разделители для комбинированных цветов
    separators = [',', ';', '/']

    # Определяем разделитель
    separator_used = None
    for sep in separators:
        if sep in value:
            separator_used = sep
            break

    if separator_used:
        # Комбинированные цвета
        parts = [p.strip() for p in value.split(separator_used)]
        harmonized_parts = []
        seen = set()

        for part in parts:
            harmonized = harmonize_single_color(part)
            if harmonized and harmonized not in seen:
                seen.add(harmonized)
                harmonized_parts.append(harmonized)

        # Объединяем через запятую (стандартный разделитель)
        return ', '.join(harmonized_parts) if harmonized_parts else ''
    else:
        # Одиночный цвет
        return harmonize_single_color(value)


# ============= ГАРМОНИЗАЦИЯ СТРУКТУРЫ =============

def harmonize_structure(value: str) -> str:
    """
    Гармонизация структуры

    Приводит к единой форме (женский род):
    "Гладкая", "Структурированная", "Рельефная", и т.д.
    """
    if not value:
        return ''

    value = value.strip().lower()

    # Основные типы структур
    if 'гладк' in value:
        return 'Гладкая'
    elif 'структур' in value:
        return 'Структурированная'
    elif 'рельеф' in value:
        return 'Рельефная'
    elif 'матов' in value:
        return 'Матовая'
    elif 'глянцев' in value:
        return 'Глянцевая'
    elif 'карвинг' in value:
        return 'Карвинг'
    elif 'шероховат' in value:
        return 'Шероховатая'
    elif 'sugar' in value:
        return 'Sugar-эффект'
    elif '3d' in value:
        return '3D'
    elif 'рифлен' in value:
        return 'Рифленая'
    elif 'защит' in value and 'скольз' in value:
        return 'Противоскользящая'
    elif 'колот' in value:
        return 'Колотая'
    elif 'текстур' in value:
        return 'Текстурированная'
    elif 'без покрыт' in value:
        return 'Без покрытия'

    # По умолчанию - капитализируем
    return value.capitalize()


# ============= ГАРМОНИЗАЦИЯ БРЕНДОВ =============

def harmonize_brand(value: str) -> str:
    """
    Гармонизация названий брендов

    Правила:
    1. Убирает лишние суффиксы (RUSSIA, Life, и т.д.)
    2. Приводит к единому написанию
    3. Исправляет опечатки
    """
    if not value:
        return ''

    value = value.strip().upper()

    # Удаляем географические и прочие суффиксы
    suffixes_to_remove = [
        ' RUSSIA',
        ' LIFE',
        ' HOME',
        ' GROUP',
        ' BY ESTIMA',
        ' CERAMICHE',
        ' CERAMICA',
        ' CERAMICAS',
        ' TILES',
        ' GRES',
        ' KERAMIKA',
        ' EURO',
        ' CERA'
    ]

    original = value
    for suffix in suffixes_to_remove:
        if value.endswith(suffix):
            base = value[:-len(suffix)].strip()
            # Проверяем, что после удаления суффикса осталось значимое название
            if len(base) >= 3:
                value = base
                break

    # Словарь известных вариаций брендов
    brand_variations = {
        'ATLAS CONCORDE': 'ATLAS CONCORDE',
        'AMETIS': 'ESTIMA',  # AMETIS BY ESTIMA -> ESTIMA
        'ART CERAMIC': 'ARTCER',  # Объединяем похожие
        'ШАХТИНСКАЯ ПЛИТКА': 'GRACIA CERAMICA',  # OBI часто называет так Gracia
        'UNITILE LIFE': 'UNITILE',
        'UNITILE': 'UNITILE',
        'КЕРАМИН': 'КЕРАМИН',
        'ALMA CERAMICA': 'ALMA',
        'LB CERAMICS': 'LB',
        'IMOLA CERAMICA': 'IMOLA',
        'FAP CERAMICHE': 'FAP',
        'APE CERAMICA': 'APE',
        'ABK CERAMICHE': 'ABK',
        'REX CERAMICHE': 'REX',
        'STN CERAMICA': 'STN',
        'AVA CERAMICA': 'AVA',
        'TAU CERAMICA': 'TAU',
        'VIVES CERAMICA': 'VIVES',
        'EQUIPE CERAMICAS': 'EQUIPE',
        'LIVING CERAMICS': 'LIVING',
        'ELETTO CERAMICA': 'ELETTO',
        'ARCANA CERAMICA': 'ARCANA',
        'ARCADIA CERAMICA': 'ARCADIA',
        'MAIMOON CERAMICA': 'MAIMOON',
        'ARGENTA CERAMICA': 'ARGENTA',
        'ASCOT CERAMICHE': 'ASCOT',
        'BENADRESA AZULEJOS': 'BENADRESA',
        'CASA DOLCE CASA': 'CASA DOLCE CASA',
        'GRACIA CERAMICA': 'GRACIA',
        'GLOBAL TILE': 'GLOBAL',
        'NEW TREND': 'NEW TREND',
        'KERAMA MARAZZI': 'KERAMA MARAZZI',
        'ARTKERA GROUP': 'ARTKERA',
        'BASCONI HOME': 'BASCONI',
        'AMETIS BY ESTIMA': 'ESTIMA'
    }

    # Проверяем точное совпадение в словаре
    if value in brand_variations:
        return brand_variations[value]

    # Проверяем совпадение с ключом после удаления суффиксов
    for key, standard in brand_variations.items():
        if value.startswith(key.split()[0]) and len(key.split()[0]) >= 4:
            return standard

    return value


# ============= ГАРМОНИЗАЦИЯ НАЛИЧИЯ (кроме LemanaPRO) =============

def harmonize_availability(value: str, store: str) -> str:
    """
    Гармонизация наличия товара

    Для LemanaPRO оставляем как есть (уникальные значения)
    Для остальных магазинов приводим к стандарту
    """
    if not value:
        return ''

    # Для LemanaPRO не трогаем
    if store == 'LemanaPRO':
        return value

    value = value.strip()

    # Стандартизация для других магазинов
    if 'доступен' in value.lower() or 'наличи' in value.lower():
        return 'В наличии'
    elif 'нет' in value.lower() or 'отсутств' in value.lower():
        return 'Нет в наличии'
    else:
        return 'В наличии'


# ============= ИЗВЛЕЧЕНИЕ ОСНОВНЫХ ЭЛЕМЕНТОВ =============

def get_primary_design(design: str) -> str:
    """
    Извлекает основной (первый) дизайн из комбинации

    Примеры:
    - "Мрамор, Камень" → "Мрамор"
    - "Моноколор" → "Моноколор"
    """
    if not design:
        return ''

    # Если есть запятая, берем первый элемент
    if ',' in design:
        return design.split(',')[0].strip()

    return design.strip()


def get_primary_color(color: str) -> str:
    """
    Извлекает основной (первый) цвет из комбинации

    Примеры:
    - "Зеленый, Синий" → "Зеленый"
    - "Белый" → "Белый"
    """
    if not color:
        return ''

    # Если есть запятая, берем первый элемент
    if ',' in color:
        return color.split(',')[0].strip()

    return color.strip()


# ============= ГАРМОНИЗАЦИЯ ЦЕНЫ =============

def harmonize_price(value) -> Optional[Union[int, float]]:
    """
    Гармонизация поля цены

    Обрабатывает форматы:
    - "2 234 ₽"    → 2234
    - "2 234.01 ₽" → 2234.01
    - "2 234,01 ₽" → 2234.01
    - "999 ₽"      → 999
    - 1234         → 1234

    Пробел считается разделителем тысяч, запятая — десятичным разделителем.
    Возвращает int если нет дробной части, float если есть.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        result = float(value)
        return int(result) if result == int(result) else result

    value = str(value).strip()
    if not value:
        return None

    # Оставляем только цифры, пробелы, точки и запятые
    cleaned = re.sub(r'[^\d\s.,]', '', value).strip()

    # Заменяем запятую на точку (десятичный разделитель)
    cleaned = cleaned.replace(',', '.')

    # Убираем все виды пробелов (обычный U+0020, неразрывный U+00A0, узкий U+202F и др.)
    cleaned = re.sub(r'\s', '', cleaned)

    if not cleaned:
        return None

    try:
        result = float(cleaned)
        return int(result) if result == int(result) else result
    except ValueError:
        return None


# ============= ОСНОВНАЯ ФУНКЦИЯ ГАРМОНИЗАЦИИ =============

def harmonize_record(record: dict) -> dict:
    """
    Применяет все правила гармонизации к одной записи
    """
    # Создаем копию записи
    harmonized = record.copy()

    # Применяем гармонизацию к каждому полю
    if 'price_unit' in harmonized:
        harmonized['price_unit'] = harmonize_measurement_unit(
            harmonized.get('price_unit', '')
        )

    if 'design' in harmonized:
        harmonized['design'] = harmonize_design(
            harmonized.get('design', '')
        )

    if 'color' in harmonized:
        harmonized['color'] = harmonize_color(
            harmonized.get('color', '')
        )

    if 'surface_type' in harmonized:
        harmonized['surface_type'] = harmonize_surface_type(
            harmonized.get('surface_type', '')
        )

    if 'structure' in harmonized:
        harmonized['structure'] = harmonize_structure(
            harmonized.get('structure', '')
        )

    if 'brand' in harmonized:
        harmonized['brand'] = harmonize_brand(
            harmonized.get('brand', '')
        )

    if 'price' in harmonized:
        harmonized['price'] = harmonize_price(
            harmonized.get('price')
        )

    if 'availability' in harmonized:
        harmonized['availability'] = harmonize_availability(
            harmonized.get('availability', ''),
            harmonized.get('store', '')
        )

    # Обновляем brand_country после гармонизации бренда
    if 'brand' in harmonized and 'country' in harmonized:
        brand = harmonized.get('brand', '')
        country = harmonized.get('country', '')
        if brand and country:
            harmonized['brand_country'] = f'{brand} ({country})'
        elif brand:
            harmonized['brand_country'] = brand
        elif country:
            harmonized['brand_country'] = country

    return harmonized
