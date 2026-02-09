import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
from selenium.webdriver.common.by import By
import pickle
import undetected_chromedriver as uc
import os

# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# Определяем директорию скрипта
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
cur_data_file = datetime.now().strftime("%m.%Y")
start_time = time.time()


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


def load_existing_data(group, city):
    """Загружает существующие данные из JSON файла текущего месяца"""
    file_name = f"data_{cur_data_file}_{group}_{city}_obi.json"
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


def save_broken_urls(break_line, group, city):
    """Сохраняет сломанные ссылки в файл"""
    if break_line:
        file_path = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_{group}_{city}_obi.txt')
        with open(file_path, 'w', encoding='utf-8') as file:
            for url in break_line:
                file.write(f'{url}\n')


def save_cookies(city_list):
    options = uc.ChromeOptions()
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.media": 2
    }
    options.add_experimental_option("prefs", prefs)

    # Инициализация undetected_chromedriver с автоопределением
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=144  # Указываем версию Chrome явно
    )
    time.sleep(5)
    url = 'https://obi.ru/'
    time.sleep(2)

    try:
        for city in city_list:
            xpath_expression = f"//button[@block='StoreItems'][@elem='Item'][text()='{city}']"

            driver.get(url=url)
            time.sleep(2)
            show_password = driver.find_element(By.XPATH, "//button[@class='nbbcX']").click()
            time.sleep(1)
            email_input = driver.find_element(By.XPATH, "//button[@class='_2eEQG _2xhLm _1k0NU _3aV4_']").click()
            time.sleep(1)
            # Выбираем город из списка и клацаем
            element = driver.find_element(By.XPATH, xpath_expression).click()
            time.sleep(1)
            # записываем печеньки
            cookie_path = os.path.join(SCRIPT_DIR, f'cookies_{city}')
            pickle.dump(driver.get_cookies(), open(cookie_path, 'wb'))
    except Exception as e:
        print(f"⚠ Ошибка сохранения cookies для {city}: {e}")

    finally:
        end_driver(driver)


def get_url_tile(city_list):
    options = uc.ChromeOptions()
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.media": 2
    }
    options.add_experimental_option("prefs", prefs)

    # Инициализация undetected_chromedriver с автоопределением
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=144  # Указываем версию Chrome явно
    )
    try:
        for city in city_list:
            url = 'https://obi.ru/'
            driver.get(url=url)

            cookie_path = os.path.join(SCRIPT_DIR, f'cookies_{city}')
            for cookie in pickle.load(open(cookie_path, 'rb')):
                driver.add_cookie(cookie)
            driver.refresh()

            url_group_list = ['https://obi.ru/plitka/plitka-i-keramogranit',
                              'https://obi.ru/santehnika/unitazy-i-instaljacii',
                              'https://obi.ru/santehnika/rakoviny-i-pedestaly']

            for url in url_group_list:
                # заходим на страницу группы и собираем количество страниц
                driver.get(url=url)
                content = driver.page_source
                soup = BeautifulSoup(content, 'lxml')

                pages_counts = int(soup.find_all('a', class_='ozZNP')[-1].text)
                url_list = []
                group = url.replace('https://obi.ru/', '').replace('/', '_').replace('-', '_')

                for i in range(1, pages_counts + 1):
                    line = f'{url}?page={i}'

                    driver.get(url=line)
                    content = driver.page_source
                    soup = BeautifulSoup(content, 'lxml')
                    pages = soup.find('div', class_='_2PE29 bm0E6 _1KBT4').find_all('div', class_='FuS7R')

                    for page in pages:
                        try:
                            page_url = 'https://obi.ru' + str(page.find('a').get('href'))
                        except:
                            page_url = None
                        url_list.append(page_url)

                    print(f'Обработал {i} из {pages_counts} страниц')

                url_file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_{group}_{city}_obi.txt')
                with open(url_file_path, 'a', encoding='utf-8') as file:
                    for line in url_list:
                        file.write(f'{line}\n')

    except Exception as ex:
        print(f"✗ Ошибка при сборе ссылок: {ex}")
    finally:
        end_driver(driver)


def get_data(city_list):
    options = uc.ChromeOptions()
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.media": 2
    }
    options.add_experimental_option("prefs", prefs)

    # Инициализация undetected_chromedriver с автоопределением
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=144  # Указываем версию Chrome явно
    )

    try:
        for city in city_list:
            url = 'https://obi.ru/'
            driver.get(url=url)

            cookie_path = os.path.join(SCRIPT_DIR, f'cookies_{city}')
            for cookie in pickle.load(open(cookie_path, 'rb')):
                driver.add_cookie(cookie)
            driver.refresh()

            group_list = ['plitka_plitka_i_keramogranit',
                          'santehnika_unitazy_i_instaljacii',
                          'santehnika_rakoviny_i_pedestaly'
                          ]

            for group in group_list:
                print("\n" + "="*60)
                print(f"ОБРАБОТКА: {city} - {group}")
                print("="*60)

                # 1. Загружаем существующие данные
                data_dict = load_existing_data(group, city)
                processed_urls = get_processed_urls(data_dict)

                # 2. Читаем список URL
                url_file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_{group}_{city}_obi.txt')

                if not os.path.exists(url_file_path):
                    print(f"⚠ Файл не найден: {url_file_path}")
                    continue

                with open(url_file_path, 'r', encoding='utf-8') as file:
                    all_lines = [line.strip() for line in file.readlines()]
                    all_lines = list(set(all_lines))  # Удаляем дубликаты

                # 3. Фильтруем - пропускаем уже обработанные
                lines = [line for line in all_lines if line not in processed_urls]

                print(f"Всего URL в файле: {len(all_lines)}")
                print(f"Уже обработано: {len(processed_urls)}")
                print(f"Осталось обработать: {len(lines)}")
                print("="*60 + "\n")

                if not lines:
                    print("✓ Все URL уже обработаны!")
                    continue

                break_line = []
                file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_{group}_{city}_obi.json")
                total_urls = len(lines)
                processed_count = 0

                for idx, line in enumerate(lines, 1):
                    try:
                        print(f"\n[{idx}/{total_urls}] Загрузка: {line}")
                        driver.get(url=line)

                        try:
                            element = driver.find_element(By.XPATH, "//button[@class='_1np8r']")
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(1)
                        except:
                            pass

                        try:
                            element = driver.find_element(By.XPATH, "//button[@class='Rl-jS']")
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(1)
                        except:
                            pass

                        content = driver.page_source
                        soup = BeautifulSoup(content, 'lxml')
                        cur_data = datetime.now().strftime("%d.%m.%Y")
                        cur_time = datetime.now().strftime("%H:%M")

                        try:
                            name = soup.find("h2", class_='_3LdDm').text.strip()
                        except:
                            name = "None"

                        try:
                            price_units = soup.find("span", class_='_3SDdj').text.strip()
                        except:
                            price_units = 'Error'

                        try:
                            new_price = soup.find("span", class_='_3IeOW').text.strip()
                        except:
                            new_price = 'Error'

                        try:
                            sale = soup.find('div', class_='i7rKk').find('div', class_='JpZgV').text.strip()
                        except:
                            sale = None

                        try:
                            stocs = " ".join(soup.find("span", class_="_2KVcZ AX0Hx").text.strip().split())
                        except:
                            stocs = "Error"

                        try:
                            on_sale = soup.find('ul', class_='_1IX-e _1oifM').text.strip()
                        except:
                            on_sale = None

                        left_spec = []
                        right_spec = []

                        specs = soup.find('div', class_='_275gt').find_all('dt')
                        for spec in specs:
                            spec = " ".join(spec.text.strip().split())
                            left_spec.append(spec)

                        rspecs = soup.find('div', class_='_275gt').find_all('dd')
                        for rspec in rspecs:
                            rspec = " ".join(rspec.text.strip().split())
                            right_spec.append(rspec)
                        specs_dict = {left_spec[i].strip(): right_spec[i].strip() for i in range(len(left_spec))}

                        left_stocks = []
                        right_stocks = []
                        stocs_counter = 0

                        # собираем склады
                        try:
                            quant_stock = soup.find_all('div', class_='_2cZg4')
                            for spec in quant_stock:
                                lspec = spec.find("span", class_='_1u7d6').text.strip()
                                left_stocks.append(lspec)
                                rspec = spec.find("span", class_='_2KVcZ AX0Hx').text.strip()
                                right_stocks.append(rspec)

                                try:
                                    stocs_counter += keep_only_digits_as_int(rspec)
                                except:
                                    pass

                            quant_stock_dict = {left_stocks[i].strip(): right_stocks[i].strip() for i in
                                                range(len(right_stocks))}
                        except:
                            quant_stock_dict = {}

                        data = {
                            "Полное наименование": name,
                            "Действующая цена": new_price,
                            "Размер скидки": sale,
                            "Единица измерения цены": price_units,
                            "В наличии": stocs,
                            "Ссылка": line,
                            "Дата мониторинга": cur_data,
                            "Время мониторинга": cur_time,
                            "Магазин": "OBI",
                            "Город": city,
                            'Распродажа': on_sale,
                            "Общий остаток": stocs_counter
                        }

                        data_dict.append(data | specs_dict | quant_stock_dict)

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
                    save_broken_urls(break_line, group, city)

    except Exception as ex:
        print(f"✗ Критическая ошибка: {ex}")
    finally:
        end_driver(driver)


def retry_broken_urls(city_list):
    """Повторная попытка обработки сломанных ссылок"""
    options = uc.ChromeOptions()
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.media": 2
    }
    options.add_experimental_option("prefs", prefs)

    # Инициализация undetected_chromedriver с автоопределением
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=144  # Указываем версию Chrome явно
    )

    try:
        for city in city_list:
            url = 'https://obi.ru/'
            driver.get(url=url)

            cookie_path = os.path.join(SCRIPT_DIR, f'cookies_{city}')
            for cookie in pickle.load(open(cookie_path, 'rb')):
                driver.add_cookie(cookie)
            driver.refresh()

            group_list = ['plitka_plitka_i_keramogranit',
                          'santehnika_unitazy_i_instaljacii',
                          'santehnika_rakoviny_i_pedestaly'
                          ]

            for group in group_list:
                print("\n" + "="*60)
                print(f"ПОВТОРНАЯ ОБРАБОТКА: {city} - {group}")
                print("="*60)

                # 1. Загружаем существующие данные
                data_dict = load_existing_data(group, city)
                processed_urls = get_processed_urls(data_dict)

                # 2. Проверяем наличие файла со сломанными ссылками
                broken_urls_file = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_{group}_{city}_obi.txt')

                if not os.path.exists(broken_urls_file):
                    print(f"✓ Файл со сломанными ссылками не найден")
                    continue

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
                    continue

                break_line = []
                file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_{group}_{city}_obi.json")
                total_urls = len(lines)
                processed_count = 0

                # 5. Обрабатываем каждый сломанный URL
                for idx, line in enumerate(lines, 1):
                    try:
                        print(f"\n[{idx}/{total_urls}] Повторная загрузка: {line}")
                        driver.get(url=line)
                        time.sleep(3)  # Увеличенное ожидание для проблемных ссылок

                        try:
                            element = driver.find_element(By.XPATH, "//button[@class='_1np8r']")
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(1)
                        except:
                            pass

                        try:
                            element = driver.find_element(By.XPATH, "//button[@class='Rl-jS']")
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(1)
                        except:
                            pass

                        content = driver.page_source
                        soup = BeautifulSoup(content, 'lxml')
                        cur_data = datetime.now().strftime("%d.%m.%Y")
                        cur_time = datetime.now().strftime("%H:%M")

                        try:
                            name = soup.find("h2", class_='_3LdDm').text.strip()
                        except:
                            name = "None"

                        if name == "None":
                            print(f"⚠ Пропуск: название по-прежнему недоступно")
                            break_line.append(line)
                            continue

                        try:
                            price_units = soup.find("span", class_='_3SDdj').text.strip()
                        except:
                            price_units = 'Error'

                        try:
                            new_price = soup.find("span", class_='_3IeOW').text.strip()
                        except:
                            new_price = 'Error'

                        try:
                            sale = soup.find('div', class_='i7rKk').find('div', class_='JpZgV').text.strip()
                        except:
                            sale = None

                        try:
                            stocs = " ".join(soup.find("span", class_="_2KVcZ AX0Hx").text.strip().split())
                        except:
                            stocs = "Error"

                        try:
                            on_sale = soup.find('ul', class_='_1IX-e _1oifM').text.strip()
                        except:
                            on_sale = None

                        left_spec = []
                        right_spec = []

                        specs = soup.find('div', class_='_275gt').find_all('dt')
                        for spec in specs:
                            spec = " ".join(spec.text.strip().split())
                            left_spec.append(spec)

                        rspecs = soup.find('div', class_='_275gt').find_all('dd')
                        for rspec in rspecs:
                            rspec = " ".join(rspec.text.strip().split())
                            right_spec.append(rspec)
                        specs_dict = {left_spec[i].strip(): right_spec[i].strip() for i in range(len(left_spec))}

                        left_stocks = []
                        right_stocks = []
                        stocs_counter = 0

                        try:
                            quant_stock = soup.find_all('div', class_='_2cZg4')
                            for spec in quant_stock:
                                lspec = spec.find("span", class_='_1u7d6').text.strip()
                                left_stocks.append(lspec)
                                rspec = spec.find("span", class_='_2KVcZ AX0Hx').text.strip()
                                right_stocks.append(rspec)

                                try:
                                    stocs_counter += keep_only_digits_as_int(rspec)
                                except:
                                    pass

                            quant_stock_dict = {left_stocks[i].strip(): right_stocks[i].strip() for i in
                                                range(len(right_stocks))}
                        except:
                            quant_stock_dict = {}

                        data = {
                            "Полное наименование": name,
                            "Действующая цена": new_price,
                            "Размер скидки": sale,
                            "Единица измерения цены": price_units,
                            "В наличии": stocs,
                            "Ссылка": line,
                            "Дата мониторинга": cur_data,
                            "Время мониторинга": cur_time,
                            "Магазин": "OBI",
                            "Город": city,
                            'Распродажа': on_sale,
                            "Общий остаток": stocs_counter
                        }

                        data_dict.append(data | specs_dict | quant_stock_dict)

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
                    save_broken_urls(break_line, group, city)
                    print(f"\n✓ Обновлён список сломанных ссылок: {len(break_line)} шт.")
                else:
                    # Удаляем файл со сломанными ссылками, если все успешно
                    try:
                        if os.path.exists(broken_urls_file):
                            os.remove(broken_urls_file)
                            print(f"\n✓ Все ссылки успешно обработаны! Файл {broken_urls_file} удалён.")
                    except:
                        pass

    except Exception as ex:
        print(f"✗ Критическая ошибка: {ex}")
    finally:
        end_driver(driver)


def choice_the_cities():
    city_list = ['Москва', 'Санкт-Петербург', 'Казань', 'Волгоград', 'Екатеринбург', 'Краснодар']

    def show_cities():
        print("\nТекущий список городов:")
        for i, city in enumerate(city_list, 1):
            print(f"{i}. {city}")

    def remove_mode():
        while True:
            show_cities()
            if len(city_list) <= 1:
                break

            try:
                num = int(input("\nВведите номер города для удаления (0 - отмена): "))
                if num == 0:
                    break
                elif 1 <= num <= len(city_list):
                    removed = city_list.pop(num - 1)
                    print(f"Удалён: {removed}")
                else:
                    print("Ошибка: неверный номер")
            except ValueError:
                print("Ошибка: введите число")

    def select_single_mode():
        show_cities()
        while len(city_list) > 1:
            try:
                num = int(input("\nВведите номер города для сохранения: "))
                if 1 <= num <= len(city_list):
                    city_list[:] = [city_list[num - 1]]  # Оставляем только выбранный
                    print(f"Выбран город: {city_list[0]}")
                    break
                else:
                    print("Ошибка: неверный номер")
            except ValueError:
                print("Ошибка: введите число")

    # Основной цикл
    while True:
        show_cities()
        print("\n1 - Удалять города")
        print("2 - Оставить только один город")
        print("3 - Завершить")

        choice = input("Выберите действие (1-3): ")

        if choice == '1':
            remove_mode()
        elif choice == '2':
            select_single_mode()
        elif choice == '3':
            break
        else:
            print("Ошибка: выберите 1, 2 или 3")

    print("\nИтоговый список городов:")
    for city in city_list:
        print(f"- {city}")
    print()
    return city_list
    print('Начинаю исследование в выбранных городах в сети OBI')


def main():
    city_list = choice_the_cities()
    coockie_question = input('Вы желаете обновить coockie файлы подключения к городам в списке? ("1" - Да; "0" - Нет): ')
    if coockie_question == "1":
        save_cookies(city_list)

    # 1. Сбор ссылок из каталога
    get_url_tile(city_list)

    # 2. Основная обработка всех ссылок
    get_data(city_list)

    # 3. Повторная обработка сломанных ссылок
    retry_question = input('\nВы желаете повторить обработку сломанных ссылок? ("1" - Да; "0" - Нет): ')
    if retry_question == "1":
        retry_broken_urls(city_list)


if __name__ == '__main__':
    main()
    finish_time = time.time() - start_time
    print(f"Затраченное {round(finish_time)} секунд на работу скрипта")
