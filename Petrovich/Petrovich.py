import json
import time
import os
import pickle
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
COOKIES_FILE = os.path.join(SCRIPT_DIR, 'petrovich_cookies.pkl')
cur_data_file = datetime.now().strftime("%m.%Y")


def keep_only_digits_as_int(input_string):
    digits_str = ''.join(filter(str.isdigit, input_string))
    return int(digits_str) if digits_str else 0  # Если цифр нет, вернёт 0


def end_driver(driver):
    """Безопасное закрытие драйвера браузера"""
    try:
        if driver:
            driver.quit()
            time.sleep(0.5)
    except Exception:
        # Игнорируем ошибки закрытия, например "Неверный дескриптор"
        pass


def save_cookies(driver):
    """Сохраняет cookies браузера в файл"""
    with open(COOKIES_FILE, 'wb') as f:
        pickle.dump(driver.get_cookies(), f)
    print("[OK] Cookies сохранены в petrovich_cookies.pkl")


def load_cookies(driver):
    """Загружает cookies из файла в браузер"""
    if not os.path.exists(COOKIES_FILE):
        return False
    try:
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            # Удаляем проблемные поля, которые могут вызвать ошибку
            cookie.pop('sameSite', None)
            cookie.pop('storeId', None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        print("[OK] Cookies загружены из файла")
        return True
    except Exception as e:
        print(f"[!] Ошибка загрузки cookies: {e}")
        return False


def _create_driver(block_images=True):
    """Создает драйвер с опциональной блокировкой изображений"""
    options = uc.ChromeOptions()
    if block_images:
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.media": 2
        }
        options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=144
    )
    return driver


def init_driver_with_cookies():
    """Создает драйвер и загружает cookies, при необходимости просит решить капчу"""

    # 1. Пробуем быстрый путь: драйвер с блокировкой картинок + cookies
    if os.path.exists(COOKIES_FILE):
        driver = _create_driver(block_images=True)
        driver.get("https://petrovich.ru")
        time.sleep(2)
        load_cookies(driver)
        driver.get("https://petrovich.ru")
        time.sleep(2)

        if not _is_captcha_present(driver):
            print("[OK] Cookies работают, капчи нет")
            return driver

        # Cookies не помогли -- закрываем этот драйвер
        print("[!] Cookies устарели, нужно решить капчу заново")
        end_driver(driver)

    # 2. Открываем браузер С картинками для решения капчи
    print("[...] Открываю браузер с картинками для решения капчи...")
    driver = _create_driver(block_images=False)
    driver.get("https://petrovich.ru")
    time.sleep(2)

    if _is_captcha_present(driver):
        _wait_for_manual_captcha(driver)
    save_cookies(driver)
    end_driver(driver)

    # 3. Создаем рабочий драйвер БЕЗ картинок + свежие cookies
    driver = _create_driver(block_images=True)
    driver.get("https://petrovich.ru")
    time.sleep(2)
    load_cookies(driver)
    driver.get("https://petrovich.ru")
    time.sleep(2)
    print("[OK] Рабочий драйвер готов")

    return driver


def _is_captcha_present(driver):
    """Проверяет, есть ли капча на странице"""
    page_source = driver.page_source.lower()
    captcha_signs = ['captcha', 'recaptcha', 'challenge', 'smartcaptcha', 'checkbox-captcha']
    return any(sign in page_source for sign in captcha_signs)


def _wait_for_manual_captcha(driver):
    """Ожидает ручного решения капчи пользователем"""
    print("\n" + "=" * 60)
    print("ОБНАРУЖЕНА КАПЧА!")
    print("Пожалуйста, решите капчу в открытом браузере.")
    print("После решения нажмите Enter здесь...")
    print("=" * 60)
    input("> ")
    time.sleep(2)
    print("[OK] Капча решена, продолжаем работу")


def load_existing_data(group):
    """Загружает существующие данные из JSON файла текущего месяца"""
    file_name = f"data_{cur_data_file}_{group}_Petrovich.json"
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


def save_broken_urls(break_line, group):
    """Сохраняет сломанные ссылки в файл"""
    if break_line:
        file_path = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_{group}_Petrovich.txt')
        with open(file_path, 'w', encoding='utf-8') as file:
            for url in break_line:
                file.write(f'{url}\n')


def choice_group():
    available_groups = [
        "1351/?material=glazurovannyi_keramogranit|keramika|keramicheskaya_plitka|klinker|tehnicheskii_keramogranit",
        # Плитка
        "226931838",  # Раковины с тумбой
        "7172",  # Инсталляции с тумбой
        "177625593",  # Унитазы
        "245811690"  # умывальники
    ]

    legends_group = [
        "Плитка",
        "Раковины с тумбой",
        "Инсталляции для унитазов",
        "Унитазы",
        "Умывальники"
    ]

    # Список для выбранных групп

    selected_groups = []

    print("Доступные группы для выбора:")
    for i, group in enumerate(legends_group, 1):
        print(f"{i}. {group}")

    print("\nВведите номера групп, которые хотите включить (через пробел):")
    user_input = input("> ")

    try:
        # Преобразуем ввод пользователя в список номеров
        chosen_indices = list(map(int, user_input.split()))

        # Добавляем выбранные группы в список
        for index in chosen_indices:
            if 1 <= index <= len(available_groups):
                selected_groups.append(available_groups[index - 1])
            else:
                print(f"Предупреждение: номер {index} недопустим и будет пропущен")

        print("\nВыбранные группы:")
        for group in selected_groups:
            print(f"- {group}")
        print("Не смотри на эти цифры, это нужно на программном уровне:)")
        print("Начинаю работать...\n")

    except ValueError:
        print("Ошибка: пожалуйста, вводите только числа, разделенные пробелами")
    return selected_groups


def get_pages(group):
    driver = init_driver_with_cookies()

    try:

        url = f'https://petrovich.ru/catalog/{group}/'
        driver.get(url=url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(1)
        content = driver.page_source
        soup = BeautifulSoup(content, 'lxml')

        try:
            pages_count = int(keep_only_digits_as_int(soup.find('p', {'data-test': "products-counter"}).text)) / 20
            pages_count = int(pages_count) + (pages_count > int(pages_count))
            # print(pages_count)
        except:
            pages_count = 1

        url_list = []
        for i in range(pages_count):
            print(f'Обрабатываю {i} страницу каталога {group}')
            url = f'https://petrovich.ru/catalog/{group}/?sort=popularity_desc&p={i}'
            driver.get(url=url)
            content = driver.page_source
            soup = BeautifulSoup(content, 'lxml')
            pages = soup.find_all('a', {'data-test': "product-link"})

            for page in pages:
                url = page.get('href')
                url_list.append('https://petrovich.ru' + url + '#properties')

        url_list = list(set(url_list))

        if group == '1351/?material=glazurovannyi_keramogranit|keramika|keramicheskaya_plitka|klinker|tehnicheskii_keramogranit':
            group = 'plitka'
        elif group == '226931838':
            group = 'rakovinyandtumby'
        elif group == '7172':
            group = 'instaliyatsiforunitazy'
        elif group == '177625593':
            group = 'unitay'
        else:
            group = 'umivalniki'

        url_file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_{group}_Petrovich.txt')
        with open(url_file_path, 'a', encoding='utf-8') as file:
            for line in url_list:
                file.write(f'{line}\n')

    except Exception as ex:
        print(f"✗ Ошибка при сборе ссылок: {ex}")
    finally:
        end_driver(driver)


def get_data(group):
    # Нормализация имени группы
    if group == '1351/?material=glazurovannyi_keramogranit|keramika|keramicheskaya_plitka|klinker|tehnicheskii_keramogranit':
        group = 'plitka'
    elif group == '226931838':
        group = 'rakovinyandtumby'
    elif group == '7172':
        group = 'instaliyatsiforunitazy'
    elif group == '177625593':
        group = 'unitay'
    else:
        group = 'umivalniki'

    driver = init_driver_with_cookies()

    try:
        print("\n" + "="*60)
        print(f"ОБРАБОТКА: {group}")
        print("="*60)

        # 1. Загружаем существующие данные
        data_dict = load_existing_data(group)
        processed_urls = get_processed_urls(data_dict)

        # 2. Читаем список URL
        url_file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_{group}_Petrovich.txt')

        if not os.path.exists(url_file_path):
            print(f"⚠ Файл не найден: {url_file_path}")
            return

        with open(url_file_path, 'r', encoding='utf-8') as file:
            all_lines = [line.strip() for line in file.readlines()]

        # 3. Фильтруем - пропускаем уже обработанные
        lines = [line for line in all_lines if line not in processed_urls]

        print(f"Всего URL в файле: {len(all_lines)}")
        print(f"Уже обработано: {len(processed_urls)}")
        print(f"Осталось обработать: {len(lines)}")
        print("="*60 + "\n")

        if not lines:
            print("✓ Все URL уже обработаны!")
            return

        break_line = []
        file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_{group}_Petrovich.json")
        total_urls = len(lines)
        processed_count = 0

        for idx, line in enumerate(lines, 1):
            try:
                print(f"\n[{idx}/{total_urls}] Загрузка: {line}")
                driver.get(url=line)
                time.sleep(0.5)

                content = driver.page_source
                soup = BeautifulSoup(content, 'lxml')
                cur_data = datetime.now().strftime("%d.%m.%Y")
                cur_time = datetime.now().strftime("%H:%M")

                try:
                    name = soup.find("h1").text.strip()
                except:
                    name = None

                try:
                    price_units = soup.find('span',{'data-test':'alt-unit-tab'}).text.strip()
                except:
                    try:
                        price_units = soup.find('p',{'data-test':'default-unit-tab'}).text.strip()
                    except:
                        price_units = None

                try:
                    new_price = soup.find('div', class_='sale-block').find('p').text.strip()
                    old_price = soup.find('div', class_='sale-block').find('div',
                                                                           class_='sale-block-previous').text.strip()
                except:
                    new_price = soup.find('div', {'data-test': 'price-block'}).find('p', {
                        'data-test': 'product-gold-price'}).text.strip()
                    old_price = None

                try:
                    price_box = soup.find('div', class_='units-hint').find('span',
                                                                           class_='pt-nowrap tooltip').text.strip()
                except:
                    price_box = None

                left_spec = []
                right_spec = []

                specs = soup.find('ul', class_='product-properties-list listing-data').find_all('li', class_ = 'data-item')
                for spec in specs:
                    lspec = spec.find("div", class_='title').text.strip()
                    left_spec.append(lspec)
                    rspec = spec.find("div", class_='value').text.strip()
                    right_spec.append(rspec)

                specs_dict = {left_spec[i].strip(): right_spec[i].strip() for i in range(len(left_spec))}

                # собираем склады
                stocks_counter = 0
                try:
                    quant_stock = soup.find('div', class_='product-sidebar-content m-desktop').find('span', class_='pt-split-sm-xs-s pt-y-center').find('p', {'data-test':'typography'}).text.strip()

                    try:
                        stocks_counter += keep_only_digits_as_int(quant_stock)
                    except:
                        pass

                except:
                    pass

                data = {
                    "Полное наименование": name,
                    "Действующая цена": new_price,
                    "Цена без скидки": old_price,
                    'Продается коробками по': price_box,
                    "Единица измерения цены": price_units,
                    "Ссылка": line,
                    "Дата мониторинга": cur_data,
                    "Время мониторинга": cur_time,
                    "Магазин": "Petrovich",
                    "Общий остаток": stocks_counter
                }

                data_dict.append(data | specs_dict)

                # СОХРАНЕНИЕ ПОСЛЕ КАЖДОЙ КАРТОЧКИ (защита от сбоев)
                save_data_incrementally(data_dict, file_path)

                # РЕЗЕРВНОЕ КОПИРОВАНИЕ каждые 1000 записей
                if len(data_dict) % 1000 == 0:
                    save_backup_copy(data_dict, file_path)

                print(f'✓ Обработано: {idx}/{total_urls} | Всего в базе: {len(data_dict)}')
                processed_count += 1

            except Exception as e:
                break_line.append(line)
                print(f'✗ Ошибка ({idx}/{total_urls}): {str(e)[:100]}')
                # Даже при ошибке сохраняем то, что успели
                save_data_incrementally(data_dict, file_path)

        print(f'\n✓ Обработано новых: {processed_count}')
        print(f'✗ Ошибок: {len(break_line)}')
        print(f'✓ Всего в базе: {len(data_dict)}')

        # Финальная резервная копия
        if len(data_dict) > 0:
            save_backup_copy(data_dict, file_path)

        # Сохраняем сломанные ссылки
        if break_line:
            save_broken_urls(break_line, group)

    except Exception as ex:
        print(f"✗ Критическая ошибка: {ex}")
        # Сохраняем даже при критической ошибке
        if 'file_path' in locals() and 'data_dict' in locals():
            save_data_incrementally(data_dict, file_path)
    finally:
        end_driver(driver)


def retry_broken_urls(group):
    """Повторная попытка обработки сломанных ссылок"""
    # Нормализация имени группы
    if group == '1351/?material=glazurovannyi_keramogranit|keramika|keramicheskaya_plitka|klinker|tehnicheskii_keramogranit':
        group = 'plitka'
    elif group == '226931838':
        group = 'rakovinyandtumby'
    elif group == '7172':
        group = 'instaliyatsiforunitazy'
    elif group == '177625593':
        group = 'unitay'
    else:
        group = 'umivalniki'

    driver = init_driver_with_cookies()

    try:
        print("\n" + "="*60)
        print(f"ПОВТОРНАЯ ОБРАБОТКА: {group}")
        print("="*60)

        # 1. Загружаем существующие данные
        data_dict = load_existing_data(group)
        processed_urls = get_processed_urls(data_dict)

        # 2. Проверяем наличие файла со сломанными ссылками
        broken_urls_file = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_{group}_Petrovich.txt')

        if not os.path.exists(broken_urls_file):
            print(f"✓ Файл со сломанными ссылками не найден")
            return

        # 3. Читаем список сломанных URL
        with open(broken_urls_file, 'r', encoding='utf-8') as file:
            all_broken_urls = [line.strip() for line in file.readlines() if line.strip()]

        # 4. Фильтруем - пропускаем уже обработанные
        lines = [line for line in all_broken_urls if line not in processed_urls]

        print(f"Всего сломанных URL: {len(all_broken_urls)}")
        print(f"Уже обработано ранее: {len(all_broken_urls) - len(lines)}")
        print(f"К повторной обработке: {len(lines)}")
        print("="*60 + "\n")

        if not lines:
            print("✓ Все сломанные URL уже обработаны!")
            return

        break_line = []
        file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_{group}_Petrovich.json")
        total_urls = len(lines)
        processed_count = 0

        # 5. Обрабатываем каждый сломанный URL
        for idx, line in enumerate(lines, 1):
            try:
                print(f"\n[{idx}/{total_urls}] Повторная загрузка: {line}")
                driver.get(url=line)
                time.sleep(3)  # Увеличенное ожидание для проблемных ссылок

                content = driver.page_source
                soup = BeautifulSoup(content, 'lxml')
                cur_data = datetime.now().strftime("%d.%m.%Y")
                cur_time = datetime.now().strftime("%H:%M")

                try:
                    name = soup.find("h1").text.strip()
                except:
                    name = None

                if not name:
                    print(f"⚠ Пропуск: название по-прежнему недоступно")
                    break_line.append(line)
                    continue

                try:
                    price_units = soup.find('span',{'data-test':'alt-unit-tab'}).text.strip()
                except:
                    try:
                        price_units = soup.find('p',{'data-test':'default-unit-tab'}).text.strip()
                    except:
                        price_units = None

                try:
                    new_price = soup.find('div', class_='sale-block').find('p').text.strip()
                    old_price = soup.find('div', class_='sale-block').find('div',
                                                                           class_='sale-block-previous').text.strip()
                except:
                    new_price = soup.find('div', {'data-test': 'price-block'}).find('p', {
                        'data-test': 'product-gold-price'}).text.strip()
                    old_price = None

                try:
                    price_box = soup.find('div', class_='units-hint').find('span',
                                                                           class_='pt-nowrap tooltip').text.strip()
                except:
                    price_box = None

                left_spec = []
                right_spec = []

                specs = soup.find('ul', class_='product-properties-list listing-data').find_all('li', class_ = 'data-item')
                for spec in specs:
                    lspec = spec.find("div", class_='title').text.strip()
                    left_spec.append(lspec)
                    rspec = spec.find("div", class_='value').text.strip()
                    right_spec.append(rspec)

                specs_dict = {left_spec[i].strip(): right_spec[i].strip() for i in range(len(left_spec))}

                # собираем склады
                stocks_counter = 0
                try:
                    quant_stock = soup.find('div', class_='product-sidebar-content m-desktop').find('span', class_='pt-split-sm-xs-s pt-y-center').find('p', {'data-test':'typography'}).text.strip()

                    try:
                        stocks_counter += keep_only_digits_as_int(quant_stock)
                    except:
                        pass

                except:
                    pass

                data = {
                    "Полное наименование": name,
                    "Действующая цена": new_price,
                    "Цена без скидки": old_price,
                    'Продается коробками по': price_box,
                    "Единица измерения цены": price_units,
                    "Ссылка": line,
                    "Дата мониторинга": cur_data,
                    "Время мониторинга": cur_time,
                    "Магазин": "Petrovich",
                    "Общий остаток": stocks_counter
                }

                data_dict.append(data | specs_dict)

                # СОХРАНЕНИЕ ПОСЛЕ КАЖДОЙ КАРТОЧКИ
                save_data_incrementally(data_dict, file_path)

                # РЕЗЕРВНОЕ КОПИРОВАНИЕ каждые 1000 записей
                if len(data_dict) % 1000 == 0:
                    save_backup_copy(data_dict, file_path)

                print(f"✓ Успешно обработано [{idx}/{total_urls}]")
                processed_count += 1

            except Exception as e:
                break_line.append(line)
                print(f'✗ Ошибка повторной обработки ({idx}/{total_urls}): {str(e)[:100]}')
                save_data_incrementally(data_dict, file_path)

        print(f'\n{"="*60}')
        print(f'✓ Успешно обработано: {processed_count}')
        print(f'✗ Всё ещё сломано: {len(break_line)}')
        print(f'✓ Всего записей в базе: {len(data_dict)}')
        print("="*60)

        # Финальная резервная копия
        if len(data_dict) > 0:
            save_backup_copy(data_dict, file_path)

        # Обновляем список сломанных ссылок
        if break_line:
            save_broken_urls(break_line, group)
            print(f"\n✓ Обновлён список сломанных ссылок: {len(break_line)} шт.")
        else:
            # Удаляем файл со сломанными ссылками, если все успешно
            try:
                if os.path.exists(broken_urls_file):
                    os.remove(broken_urls_file)
                    print(f"\n✓ Все ссылки успешно обработаны! Файл удалён.")
            except:
                pass

    except Exception as ex:
        print(f"✗ Критическая ошибка: {ex}")
        # Сохраняем даже при критической ошибке
        if 'file_path' in locals() and 'data_dict' in locals():
            save_data_incrementally(data_dict, file_path)
    finally:
        end_driver(driver)


def main():
    selected_groups = choice_group()

    # 1. Сбор ссылок из каталога (раскомментируйте при необходимости)
    for group in selected_groups:
        get_pages(group)

    # 2. Основная обработка всех ссылок
    for group in selected_groups:
        get_data(group)

    # 3. Повторная обработка сломанных ссылок
    retry_question = input('\nВы желаете повторить обработку сломанных ссылок? ("1" - Да; "0" - Нет): ')
    if retry_question == "1":
        for group in selected_groups:
            retry_broken_urls(group)


if __name__ == '__main__':
    main()
    finish_time = time.time() - start_time
    print(f"Затраченное на работу скрипта время: {finish_time}")
