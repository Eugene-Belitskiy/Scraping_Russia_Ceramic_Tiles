import json
import time
import os
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

start_time = time.time()

# Определяем директорию скрипта
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
cur_data_file = datetime.now().strftime("%m.%Y")

options = uc.ChromeOptions()
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.default_content_setting_values.images": 2,
    "profile.managed_default_content_settings.media": 2
}
options.add_experimental_option("prefs", prefs)

# Инициализация undetected_chromedriver
driver = uc.Chrome(
    options=options,
    use_subprocess=True,
    version_main=144  # Указываем версию Chrome явно
)
time.sleep(5)


def end_driver():
    """Безопасное закрытие драйвера браузера"""
    try:
        if driver:
            driver.quit()
            time.sleep(0.5)
    except Exception:
        # Игнорируем ошибки закрытия, например "Неверный дескриптор"
        pass


def load_existing_data():
    """Загружает существующие данные из JSON файла текущего месяца"""
    file_name = f"data_{cur_data_file}_Tiles_LemanaPRO.json"
    file_path = os.path.join(SCRIPT_DIR, file_name)

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✓ Загружен существующий файл: {file_name}")
            print(f"✓ Найдено записей: {len(data)}")
            return data
        except Exception as e:
            print(f"⚠ Ошибка при чтении файла: {e}")
            return []
    else:
        print(f"Файл {file_name} не найден, начинаем с нуля")
        return []


def get_processed_urls(existing_data):
    """Извлекает список уже обработанных URL из существующих данных"""
    processed = set()
    for item in existing_data:
        if 'Ссылка' in item and item['Ссылка']:
            processed.add(item['Ссылка'])
    print(f"✓ Уже обработано URL: {len(processed)}")
    return processed


def save_data_incrementally(data_dict, file_path):
    """Сохраняет данные после каждой обработанной карточки с принудительной записью на диск"""
    try:
        # Сначала записываем во временный файл
        temp_file = file_path + '.tmp'
        with open(temp_file, 'w', encoding="utf-8") as json_file:
            json.dump(data_dict, json_file, indent=4, ensure_ascii=False)
            json_file.flush()  # Принудительно сбрасываем буфер Python
            os.fsync(json_file.fileno())  # Принудительно записываем на диск (OS level)

        # Атомарная замена: если запись успешна, заменяем основной файл
        if os.path.exists(file_path):
            os.replace(temp_file, file_path)
        else:
            os.rename(temp_file, file_path)

    except Exception as e:
        print(f"✗ Ошибка при сохранении: {e}")
        # Удаляем временный файл в случае ошибки
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


def save_backup_copy(data_dict, file_path):
    """Создает резервную копию, которая перезаписывается при каждом вызове"""
    try:
        backup_path = file_path.replace('.json', '_BACKUP.json')
        temp_backup = backup_path + '.tmp'

        with open(temp_backup, 'w', encoding="utf-8") as json_file:
            json.dump(data_dict, json_file, indent=4, ensure_ascii=False)
            json_file.flush()
            os.fsync(json_file.fileno())

        # Заменяем старую резервную копию новой
        if os.path.exists(backup_path):
            os.replace(temp_backup, backup_path)
        else:
            os.rename(temp_backup, backup_path)

        print(f"💾 Резервная копия обновлена: {len(data_dict)} записей")

    except Exception as e:
        print(f"⚠ Ошибка создания резервной копии: {e}")
        if os.path.exists(temp_backup):
            try:
                os.remove(temp_backup)
            except:
                pass


def keep_only_digits_as_int(input_string):
    digits_str = ''.join(filter(str.isdigit, input_string))
    return int(digits_str) if digits_str else 0


def safe_find(soup, *args, **kwargs):
    """Безопасное извлечение данных с обработкой исключений"""
    try:
        element = soup.find(*args, **kwargs)
        return element.text.strip() if element else None
    except (AttributeError, Exception):
        return None


def retry_click(driver, xpath, max_attempts=3, wait_time=2):
    """Повторные попытки клика по элементу с ожиданием"""
    for attempt in range(max_attempts):
        try:
            # Ждем появления элемента до 10 секунд
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            # Дополнительная задержка для загрузки
            time.sleep(1)
            # Скроллим к элементу
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            # Кликаем через JavaScript
            driver.execute_script("arguments[0].click();", element)
            time.sleep(1)  # Ждем после клика
            return True
        except Exception as e:
            print(f"Попытка клика {attempt + 1}/{max_attempts}: {str(e)[:50]}")
            if attempt == max_attempts - 1:
                raise
            time.sleep(wait_time)
    return False


def parse_price(soup):
    """Извлекает цену, скидку и единицы измерения"""
    new_price = None
    discount = None
    price_units = None

    price_selectors = [
        # Вариант 1: с блоком скидки
        (
            lambda s: s.find('div', {'data-qa': 'prices_mf-pdp'}).find('div', {'data-testid': 'price-block-price'}).find('span', {'data-testid': 'price'}),
        ),
        # Вариант 2: без блока скидки
        (
            lambda s: s.find('div', {'data-qa': 'prices_mf-pdp'}).find('span', {'data-testid': 'price'}),
        ),
        # Вариант 3: цена за единицу
        (
            lambda s: s.find('div', {'data-qa': 'prices_mf-pdp'}).find('div', {'data-testid': 'price-block-unitprice'}),
        )
    ]

    for price_selector in price_selectors:
        try:
            price_element = price_selector(soup)
            if price_element:
                new_price = safe_find(price_element, 'span', {'data-testid': 'price-integer'})
                price_units = safe_find(price_element, 'span', {'data-testid': 'price-unit'})
                break
        except (AttributeError, Exception):
            continue

    # Отдельная проверка наличия скидки
    try:
        discount_block = soup.find('div', {'data-testid': 'price-block-discount'})
        if discount_block:
            discount_span = discount_block.find('span', {'data-testid': 'marker-text'})
            if discount_span:
                discount = discount_span.text.strip()
    except (AttributeError, Exception):
        pass

    return new_price, discount, price_units


def process_online_only_product(soup):
    """Обработка товара 'Только онлайн-заказ' - БЕЗ клика"""
    print("🌐 Товар только для онлайн-заказа")

    stocks_counter = 0
    stocks_mesure = None
    quant_stock_dict = {}  # Пустой - складов нет

    # Ищем "Доступно для заказа N кор./шт."
    import re
    try:
        page_text = soup.get_text()
        # Ищем паттерн
        pattern = r'доступно\s+для\s+заказа\s+(\d+)\s*(кор\.|шт\.)'
        match = re.search(pattern, page_text.lower())
        if match:
            stocks_counter = int(match.group(1))
            stocks_mesure = match.group(2)
            print(f"✓ Найдено: {stocks_counter} {stocks_mesure}")
    except Exception as e:
        print(f"⚠ Не удалось извлечь онлайн-остаток: {e}")

    return quant_stock_dict, stocks_counter, stocks_mesure


def process_store_product(driver, soup):
    """Обработка товара в магазинах - С кликом на склады"""
    print("🏪 Товар в магазинах")

    quant_stock_dict = {}
    stocks_counter = 0
    stocks_mesure = None

    try:
        # Кликаем на кнопку складов
        retry_click(driver, "//*[@data-qa='stock-in-stores-title-interactive']")

        print("Ожидание загрузки данных складов...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "m1e45js0_pdp"))
        )
        time.sleep(2)

        # Обновляем HTML после клика
        content = driver.page_source
        soup = BeautifulSoup(content, 'lxml')

        # Собираем остатки по складам
        quant_stock = soup.find_all('div', class_='m1e45js0_pdp')
        for spec in quant_stock:
            store_name = safe_find(spec, "div", class_='m19407om_pdp')
            stock_text = safe_find(spec, "span", {'data-qa': 'modal-store-item-in-stock-text'})

            if store_name and stock_text:
                quant_stock_dict[store_name] = stock_text
                stocks_counter += keep_only_digits_as_int(stock_text)

                if stocks_mesure is None:
                    stocks_mesure = 'шт.' if 'шт.' in stock_text else 'кор.'

        print(f"✓ Найдено {len(quant_stock_dict)} складов, остаток: {stocks_counter} {stocks_mesure}")

    except Exception as e:
        print(f"⚠ Ошибка при обработке складов: {e}")

    return quant_stock_dict, stocks_counter, stocks_mesure


def get_pages():
    """Собирает ссылки на товары из всех категорий"""
    groups = [
        "keramogranit",
        "keramicheskaya-plitka",
        "napolnaya-plitka",
        'nastennaya-plitka',
    ]
    url_list = []

    try:
        for group in groups:
            url = f'https://lemanapro.ru/catalogue/{group}/?deliveryType=Самовывоз+в+магазине_Пункты+выдачи_Доставка+курьером'
            driver.get(url=url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)

            content = driver.page_source
            soup = BeautifulSoup(content, 'lxml')

            # Определяем количество страниц
            try:
                pages_count = int(
                    soup.find('nav', class_='V0mKVjE3ab_plp')
                    .find('ul')
                    .find_all('span', class_='JhFg2lLR4e_plp')[-2].text
                )
            except (AttributeError, ValueError, IndexError):
                print(f"Не удалось определить количество страниц для {group}")
                continue

            # Обрабатываем каждую страницу каталога
            for page_num in range(1, pages_count + 1):
                print(f'Обрабатываю {page_num} страницу каталога {group}')
                url = f'https://lemanapro.ru/catalogue/{group}/?deliveryType=Самовывоз+в+магазине_Пункты+выдачи_Доставка+курьером&page={page_num}'
                driver.get(url=url)

                content = driver.page_source
                soup = BeautifulSoup(content, 'lxml')

                section = soup.find('section', class_='pfgfjrg_plp')
                if not section:
                    continue

                # Извлекаем основные товарные ссылки
                product_links = section.find_all('a', {'data-qa': 'product-name'})
                for link in product_links:
                    href = link.get('href')
                    if href and '/product/' in href:
                        url_list.append('https://lemanapro.ru' + href)

                # Извлекаем дополнительные ссылки из карусели
                carousel_links = section.find_all('a', class_='wAxCBuwj4T_product-carousel p5y548z_product-carousel p105rlqh_product-carousel')
                for link in carousel_links:
                    href = link.get('href')
                    if href:
                        url_list.append('https://lemanapro.ru' + href)

        # Удаляем дубликаты
        url_list = list(set(url_list))

        # Сохраняем ссылки в файл
        file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_Tiles_LemanaPRO.txt')
        with open(file_path, 'w', encoding='utf-8') as file:
            for url in url_list:
                file.write(f'{url}\n')

        print(f"Собрано уникальных ссылок: {len(url_list)}")

    except Exception as ex:
        print(f"Ошибка при сборе ссылок: {ex}")


def save_broken_urls(break_line):
    """Сохраняет сломанные ссылки в файл"""
    if break_line:
        file_path = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_Tiles_LemanaPRO.txt')
        with open(file_path, 'w', encoding='utf-8') as file:
            for url in break_line:
                file.write(f'{url}\n')


def get_data():
    """Извлекает данные о товарах из собранных ссылок с защитой от сбоев"""
    # 1. Загружаем существующие данные
    print("\n" + "="*60)
    print("ЗАГРУЗКА СУЩЕСТВУЮЩИХ ДАННЫХ")
    print("="*60)
    data_dict = load_existing_data()
    processed_urls = get_processed_urls(data_dict)

    break_line = []
    file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_Tiles_LemanaPRO.json")

    try:
        # 2. Читаем список URL
        url_file = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_Tiles_LemanaPRO.txt')

        if not os.path.exists(url_file):
            print(f"✗ Файл со списком URL не найден: {url_file}")
            print("Сначала запустите функцию get_pages() для сбора ссылок")
            return

        with open(url_file, 'r', encoding='utf-8') as file:
            all_urls = [line.strip() for line in file.readlines()]

        # 3. Фильтруем - пропускаем уже обработанные
        lines = [url for url in all_urls if url not in processed_urls]

        print(f"\n" + "="*60)
        print("СТАТИСТИКА")
        print("="*60)
        print(f"Всего URL в файле: {len(all_urls)}")
        print(f"Уже обработано: {len(processed_urls)}")
        print(f"Осталось обработать: {len(lines)}")
        print("="*60 + "\n")

        if not lines:
            print("✓ Все URL уже обработаны!")
            return

        total_urls = len(lines)
        processed_count = 0

        # 4. Обрабатываем каждый URL
        for idx, line in enumerate(lines, 1):
            try:
                print(f"\n[{idx}/{total_urls}] Загрузка: {line}")

                driver.get(url=line)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)

                content = driver.page_source
                soup = BeautifulSoup(content, 'lxml')
                cur_data = datetime.now().strftime("%d.%m.%Y")
                cur_time = datetime.now().strftime("%H:%M")

                # КЛЮЧЕВОЙ МОМЕНТ: Определяем тип товара
                online_marker = safe_find(soup, 'span', {'data-qa': 'online-order-only-message-text'})
                is_online_only = online_marker is not None

                # Извлечение основных данных
                name = safe_find(soup, "h1", {'data-qa': 'product-name'})

                # Проверка: если название не получено, пропускаем товар
                if not name:
                    print(f"⚠ Пропуск: не удалось получить название товара")
                    break_line.append(line)
                    continue

                articul = safe_find(soup, 'span', class_='t12nw7s2_pdp')
                best_price_text = safe_find(soup, "div", {'data-qa': 'productBestPriceNameplate'})
                new_price, discount, price_units = parse_price(soup)

                # Цена за коробку
                price_box = None
                try:
                    price_box_elem = soup.find('div', class_='u1bdlfxm_pdp').find('div', {'data-testid': 'price-block-unitprice'})
                    if price_box_elem:
                        price_box = safe_find(price_box_elem, 'span', {'data-testid': 'price-integer'})
                except (AttributeError, Exception):
                    pass

                # Наличие товара
                stocks = safe_find(soup, "div", class_="out-of-stock-label") or "В наличии"

                # Извлечение характеристик
                specs_dict = {}
                specs = soup.find_all('div', {'data-qa': 'characteristics-list-item'})
                for spec in specs:
                    key = safe_find(spec, "div", class_='dsqv1xm_pdp')
                    value = safe_find(spec, "div", class_='v17yx9hk_pdp')
                    if key and value:
                        specs_dict[key] = value

                # ВЫБОР СТРАТЕГИИ: Онлайн или Магазин
                if is_online_only:
                    quant_stock_dict, stocks_counter, stocks_mesure = process_online_only_product(soup)
                    product_type = "Только онлайн"
                else:
                    quant_stock_dict, stocks_counter, stocks_mesure = process_store_product(driver, soup)
                    product_type = "В магазинах"

                # Формируем данные
                data = {
                    "Полное наименование": name,
                    "Артикул": articul,
                    "Действующая цена": new_price,
                    "Скидка": discount,
                    'Цена за коробку': price_box,
                    "Единица измерения цены": price_units,
                    "Ссылка": line,
                    "Дата мониторинга": cur_data,
                    "Время мониторинга": cur_time,
                    "Магазин": "LemanaPRO",
                    "В наличии": stocks,
                    'Онлайн заказ': product_type,  # ← ЗДЕСЬ ТИП ТОВАРА
                    'Лучшая цена': best_price_text,
                    "Единица хранения на складе": stocks_mesure,
                    "Общий остаток": stocks_counter
                }

                data_dict.append(data | specs_dict | quant_stock_dict)

                # СОХРАНЕНИЕ ПОСЛЕ КАЖДОЙ КАРТОЧКИ (защита от сбоев)
                save_data_incrementally(data_dict, file_path)

                # РЕЗЕРВНОЕ КОПИРОВАНИЕ каждые 1000 записей
                if len(data_dict) % 1000 == 0:
                    save_backup_copy(data_dict, file_path)

                # Вывод
                """ print(f'{"="*60}')
                print(f'✓ Обработано: {idx}/{total_urls} | Всего в базе: {len(data_dict)}')
                print(f'{"="*60}')
                print(f'Название: {name}')
                print(f'Тип: {product_type}')
                print(f'Цена: {new_price} {price_units}')
                print(f'Остаток: {stocks_counter} {stocks_mesure}')
                print(f'Складов: {len(quant_stock_dict)}')
                print(f'{"="*60}\n') """

                processed_count += 1

            except Exception as e:
                break_line.append(line)
                print(f'✗ Ошибка ({idx}/{total_urls}): {str(e)[:100]}')
                # Даже при ошибке сохраняем то, что успели
                save_data_incrementally(data_dict, file_path)

        print(f'\n✓ Обработано новых: {processed_count}')
        print(f'✗ Ошибок: {len(break_line)}')
        print(f'✓ Всего в базе: {len(data_dict)}')

    except Exception as ex:
        print(f"✗ Критическая ошибка: {ex}")
        # Сохраняем даже при критической ошибке
        save_data_incrementally(data_dict, file_path)

    finally:
        # Финальное сохранение и статистика
        print("\n" + "="*60)
        print("ЗАВЕРШЕНИЕ РАБОТЫ")
        print("="*60)

        try:
            if os.path.exists(file_path):
                print(f"✓ Файл: {file_path}")
                print(f"✓ Записей: {len(data_dict)}")
                print(f"✓ Размер: {os.path.getsize(file_path)} байт")
            else:
                # Последняя попытка сохранения
                save_data_incrementally(data_dict, file_path)
                print(f"✓ Финальное сохранение выполнено")

            # Финальная резервная копия
            if len(data_dict) > 0:
                save_backup_copy(data_dict, file_path)

        except Exception as e:
            print(f"✗ Ошибка: {e}")

        # Сломанные ссылки
        if break_line:
            try:
                save_broken_urls(break_line)
                print(f"✓ Сломанных ссылок: {len(break_line)}")
            except:
                pass

        print("="*60 + "\n")


def retry_broken_urls():
    """Повторная попытка обработки сломанных ссылок"""
    print("\n" + "="*60)
    print("ПОВТОРНАЯ ОБРАБОТКА СЛОМАННЫХ ССЫЛОК")
    print("="*60)

    # 1. Загружаем существующие данные
    data_dict = load_existing_data()
    processed_urls = get_processed_urls(data_dict)

    break_line = []
    file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_Tiles_LemanaPRO.json")
    broken_urls_file = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_Tiles_LemanaPRO.txt')

    # 2. Проверяем наличие файла со сломанными ссылками
    if not os.path.exists(broken_urls_file):
        print(f"✓ Файл со сломанными ссылками не найден: {broken_urls_file}")
        print("✓ Нет ссылок для повторной обработки")
        return

    try:
        # 3. Читаем список сломанных URL
        with open(broken_urls_file, 'r', encoding='utf-8') as file:
            all_broken_urls = [line.strip() for line in file.readlines() if line.strip()]

        # 4. Фильтруем - пропускаем уже обработанные (на случай если они были обработаны в основном цикле)
        lines = [url for url in all_broken_urls if url not in processed_urls]

        print(f"\nВсего сломанных URL: {len(all_broken_urls)}")
        print(f"Уже обработано ранее: {len(all_broken_urls) - len(lines)}")
        print(f"К повторной обработке: {len(lines)}")
        print("="*60 + "\n")

        if not lines:
            print("✓ Все сломанные URL уже обработаны!")
            return

        total_urls = len(lines)
        processed_count = 0

        # 5. Обрабатываем каждый сломанный URL
        for idx, line in enumerate(lines, 1):
            try:
                print(f"\n[{idx}/{total_urls}] Повторная загрузка: {line}")

                driver.get(url=line)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)  # Увеличенное ожидание для проблемных ссылок

                content = driver.page_source
                soup = BeautifulSoup(content, 'lxml')
                cur_data = datetime.now().strftime("%d.%m.%Y")
                cur_time = datetime.now().strftime("%H:%M")

                # Определяем тип товара
                online_marker = safe_find(soup, 'span', {'data-qa': 'online-order-only-message-text'})
                is_online_only = online_marker is not None

                # Извлечение основных данных
                name = safe_find(soup, "h1", {'data-qa': 'product-name'})

                # Проверка: если название не получено, пропускаем товар
                if not name:
                    print(f"⚠ Пропуск: название по-прежнему недоступно")
                    break_line.append(line)
                    continue

                print(f"✓ Название получено: {name[:50]}...")

                articul = safe_find(soup, 'span', class_='t12nw7s2_pdp')
                best_price_text = safe_find(soup, "div", {'data-qa': 'productBestPriceNameplate'})
                new_price, discount, price_units = parse_price(soup)

                # Цена за коробку
                price_box = None
                try:
                    price_box_elem = soup.find('div', class_='u1bdlfxm_pdp').find('div', {'data-testid': 'price-block-unitprice'})
                    if price_box_elem:
                        price_box = safe_find(price_box_elem, 'span', {'data-testid': 'price-integer'})
                except (AttributeError, Exception):
                    pass

                # Наличие товара
                stocks = safe_find(soup, "div", class_="out-of-stock-label") or "В наличии"

                # Извлечение характеристик
                specs_dict = {}
                specs = soup.find_all('div', {'data-qa': 'characteristics-list-item'})
                for spec in specs:
                    key = safe_find(spec, "div", class_='dsqv1xm_pdp')
                    value = safe_find(spec, "div", class_='v17yx9hk_pdp')
                    if key and value:
                        specs_dict[key] = value

                # ВЫБОР СТРАТЕГИИ: Онлайн или Магазин
                if is_online_only:
                    quant_stock_dict, stocks_counter, stocks_mesure = process_online_only_product(soup)
                    product_type = "Только онлайн"
                else:
                    quant_stock_dict, stocks_counter, stocks_mesure = process_store_product(driver, soup)
                    product_type = "В магазинах"

                # Формируем данные
                data = {
                    "Полное наименование": name,
                    "Артикул": articul,
                    "Действующая цена": new_price,
                    "Скидка": discount,
                    'Цена за коробку': price_box,
                    "Единица измерения цены": price_units,
                    "Ссылка": line,
                    "Дата мониторинга": cur_data,
                    "Время мониторинга": cur_time,
                    "Магазин": "LemanaPRO",
                    "В наличии": stocks,
                    'Онлайн заказ': product_type,
                    'Лучшая цена': best_price_text,
                    "Единица хранения на складе": stocks_mesure,
                    "Общий остаток": stocks_counter
                }

                data_dict.append(data | specs_dict | quant_stock_dict)

                # СОХРАНЕНИЕ ПОСЛЕ КАЖДОЙ КАРТОЧКИ
                save_data_incrementally(data_dict, file_path)

                # РЕЗЕРВНОЕ КОПИРОВАНИЕ каждые 1000 записей
                if len(data_dict) % 1000 == 0:
                    save_backup_copy(data_dict, file_path)

                processed_count += 1

                print(f"✓ Успешно обработано [{idx}/{total_urls}]")

            except Exception as e:
                break_line.append(line)
                print(f'✗ Ошибка повторной обработки ({idx}/{total_urls}): {str(e)[:100]}')
                save_data_incrementally(data_dict, file_path)

        print(f'\n{"="*60}')
        print(f'✓ Успешно обработано: {processed_count}')
        print(f'✗ Всё ещё сломано: {len(break_line)}')
        print(f'✓ Всего записей в базе: {len(data_dict)}')
        print("="*60)

    except Exception as ex:
        print(f"✗ Критическая ошибка: {ex}")
        save_data_incrementally(data_dict, file_path)

    finally:
        # Финальная резервная копия
        try:
            if len(data_dict) > 0:
                save_backup_copy(data_dict, file_path)
        except Exception as e:
            print(f"⚠ Ошибка финального резервного копирования: {e}")

        # Обновляем список сломанных ссылок
        if break_line:
            save_broken_urls(break_line)
            print(f"\n✓ Обновлён список сломанных ссылок: {len(break_line)} шт.")
        else:
            # Удаляем файл со сломанными ссылками, если все успешно
            try:
                if os.path.exists(broken_urls_file):
                    os.remove(broken_urls_file)
                    print(f"\n✓ Все ссылки успешно обработаны! Файл {broken_urls_file} удалён.")
            except Exception:
                pass

        print("\n")


def main():
    try:
        # 1. Сбор ссылок из каталога (раскомментируйте при необходимости)
        # get_pages()

        # 2. Основная обработка всех ссылок
        get_data()

        # 3. Повторная обработка сломанных ссылок
        retry_broken_urls()

    finally:
        # Закрываем браузер ПОСЛЕ всех операций
        print("\n" + "="*60)
        print("ЗАКРЫТИЕ БРАУЗЕРА")
        print("="*60)
        end_driver()
        print("✓ Браузер закрыт")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
    finish_time = time.time() - start_time
    print(f"Затраченное на работу скрипта время: {finish_time}")