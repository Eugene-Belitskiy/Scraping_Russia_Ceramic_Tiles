import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import os
import asyncio
import aiohttp

start_time = time.time()

# Определяем директорию скрипта
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
cur_data_file = datetime.now().strftime("%m.%Y")

# Настройки для асинхронных запросов
CONCURRENT_REQUESTS = 6  # Количество одновременных запросов
REQUEST_TIMEOUT = 30  # Таймаут запроса в секундах

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}


def load_existing_data():
    """Загружает существующие данные из JSON файла текущего месяца"""
    file_name = f"data_{cur_data_file}_KeramogranitRu.json"
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


def save_broken_urls(break_line):
    """Сохраняет сломанные ссылки в файл"""
    if break_line:
        file_path = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_KeramogranitRu.txt')
        with open(file_path, 'w', encoding='utf-8') as file:
            for url in break_line:
                file.write(f'{url}\n')


async def fetch_page_async(session, url, page_num=None, total_pages=None):
    """Асинхронная загрузка страницы"""
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
            if page_num:
                print(f'Обработал {page_num} из {total_pages} страниц')
            return await response.text()
    except Exception as e:
        print(f"✗ Ошибка загрузки {url}: {str(e)[:50]}")
        return None


async def get_url_tile_async():
    """Асинхронный сбор ссылок на товары"""
    url = 'https://www.keramogranit.ru/catalog-products/keramicheskaya-plitka/'

    # Получаем количество страниц
    q = requests.get(url=url, headers=headers)
    result = q.content
    soup = BeautifulSoup(result, 'lxml')

    pages_counts = int(soup.find_all('a', class_='pager__link')[-1].text)
    print(f"Всего страниц для сбора: {pages_counts}")

    url_list = []

    # Создаем асинхронную сессию
    async with aiohttp.ClientSession() as session:
        # Создаем задачи для всех страниц
        tasks = []
        for i in range(1, pages_counts + 1):
            page_url = f'https://www.keramogranit.ru/catalog-products/keramicheskaya-plitka/?p={i}'
            tasks.append(fetch_page_async(session, page_url, i, pages_counts))

        # Выполняем все запросы параллельно с ограничением
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

        async def fetch_with_semaphore(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(*[fetch_with_semaphore(task) for task in tasks])

        # Обрабатываем результаты
        for html in results:
            if html:
                soup = BeautifulSoup(html, 'lxml')
                pages = soup.find_all('div', class_='cat-card__desc')
                for page in pages:
                    try:
                        page_url = "https://www.keramogranit.ru" + page.find('a', class_='cat-card__title-link').get('href')
                        if 'менеджеров' not in page.find('div', class_='cat-card__price').text.strip():
                            url_list.append(page_url)
                    except:
                        pass

    url_list = list(set(url_list))
    url_file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_KeramogranitRu.txt')
    with open(url_file_path, 'w', encoding='utf-8') as file:
        for line in url_list:
            file.write(f'{line}\n')

    print(f"✓ Собрано уникальных ссылок: {len(url_list)}")


def get_url_tile():
    """Синхронная обертка для асинхронной функции"""
    asyncio.run(get_url_tile_async())


async def process_product_async(session, url, data_dict, break_line, lock, file_path, idx, total):
    """Асинхронная обработка одного товара"""
    try:
        html = await fetch_page_async(session, url)
        if not html:
            async with lock:
                break_line.append(url)
            return

        soup = BeautifulSoup(html, 'lxml')
        cur_data = datetime.now().strftime("%d.%m.%Y")
        cur_time = datetime.now().strftime("%H:%M")

        try:
            name = soup.find("div", class_='page-title').text.strip()
        except:
            name = "None"

        try:
            new_price = soup.find("span", class_='cat-price__cur').text.replace(' ', '').strip()
        except:
            new_price = 'Error'

        try:
            old_price = soup.find('del', class_='cat-price__del').text.replace(' ', '').strip()
        except:
            old_price = new_price

        try:
            price_units = soup.find("span", class_='cat-price__measure').text.strip()
        except:
            price_units = 'Error'

        try:
            stocs = soup.find('span', class_='cat-availibility__in').text
        except:
            stocs = None

        left_spec = []
        right_spec = []

        specs = soup.find('div', class_='cat-article-params').find_all('dt')
        for spec in specs:
            left_spec.append(spec.text.strip())

        rspecs = soup.find('div', class_='cat-article-params').find_all('dd')
        for spec in rspecs:
            right_spec.append(spec.text.strip())

        specs_dict = {left_spec[i].strip(): right_spec[i].strip() for i in range(len(left_spec))}

        data = {
            "Полное наименование": name,
            "Действующая цена": new_price,
            'Цена без скидки': old_price,
            "Единица измерения цены": price_units,
            'В наличии': stocs,
            "Ссылка": url,
            "Дата мониторинга": cur_data,
            "Время мониторинга": cur_time,
            "Магазин": "Keramogranit_ru",
        }

        # Потокобезопасное добавление данных
        async with lock:
            data_dict.append(data | specs_dict)

            # Сохранение после каждых 50 карточек
            if len(data_dict) % 50 == 0:
                save_data_incrementally(data_dict, file_path)

            # Резервное копирование каждые 1000 записей
            if len(data_dict) % 1000 == 0:
                save_backup_copy(data_dict, file_path)

            print(f'✓ Обработано: {idx}/{total} | Всего в базе: {len(data_dict)}')

    except Exception as e:
        async with lock:
            break_line.append(url)
        print(f'✗ Ошибка ({idx}/{total}): {str(e)[:50]}')


async def get_data_async():
    """Асинхронная обработка всех товаров"""
    print("\n" + "="*60)
    print("ОБРАБОТКА ТОВАРОВ")
    print("="*60)

    # 1. Загружаем существующие данные
    data_dict = load_existing_data()
    processed_urls = get_processed_urls(data_dict)

    # 2. Читаем список URL
    url_file_path = os.path.join(SCRIPT_DIR, f'url_list_{cur_data_file}_KeramogranitRu.txt')

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
    file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_KeramogranitRu.json")
    total_urls = len(lines)

    # Создаем асинхронную сессию и блокировку для потокобезопасности
    lock = asyncio.Lock()

    async with aiohttp.ClientSession() as session:
        # Создаем задачи для всех товаров
        tasks = []
        for idx, url in enumerate(lines, 1):
            tasks.append(process_product_async(session, url, data_dict, break_line, lock, file_path, idx, total_urls))

        # Выполняем с ограничением одновременных запросов
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

        async def process_with_semaphore(task):
            async with semaphore:
                return await task

        await asyncio.gather(*[process_with_semaphore(task) for task in tasks])

    # Финальное сохранение
    print(f'\n✓ Обработано новых: {len(lines) - len(break_line)}')
    print(f'✗ Ошибок: {len(break_line)}')
    print(f'✓ Всего в базе: {len(data_dict)}')

    # Финальная резервная копия
    if len(data_dict) > 0:
        save_backup_copy(data_dict, file_path)
        save_data_incrementally(data_dict, file_path)

    # Сохраняем сломанные ссылки
    if break_line:
        save_broken_urls(break_line)


def get_data():
    """Синхронная обертка для асинхронной функции"""
    asyncio.run(get_data_async())


async def retry_broken_urls_async():
    """Асинхронная повторная обработка сломанных ссылок"""
    print("\n" + "="*60)
    print("ПОВТОРНАЯ ОБРАБОТКА СЛОМАННЫХ ССЫЛОК")
    print("="*60)

    # 1. Загружаем существующие данные
    data_dict = load_existing_data()
    processed_urls = get_processed_urls(data_dict)

    # 2. Проверяем наличие файла со сломанными ссылками
    broken_urls_file = os.path.join(SCRIPT_DIR, f'url_break_list_{cur_data_file}_KeramogranitRu.txt')

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
    file_path = os.path.join(SCRIPT_DIR, f"data_{cur_data_file}_KeramogranitRu.json")
    total_urls = len(lines)

    # Создаем асинхронную сессию с увеличенным таймаутом
    lock = asyncio.Lock()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, url in enumerate(lines, 1):
            tasks.append(process_product_async(session, url, data_dict, break_line, lock, file_path, idx, total_urls))

        # Меньше одновременных запросов для проблемных ссылок
        semaphore = asyncio.Semaphore(10)

        async def process_with_semaphore(task):
            async with semaphore:
                await asyncio.sleep(0.5)  # Дополнительная задержка
                return await task

        await asyncio.gather(*[process_with_semaphore(task) for task in tasks])

    print(f'\n{"="*60}')
    print(f'✓ Успешно обработано: {len(lines) - len(break_line)}')
    print(f'✗ Всё ещё сломано: {len(break_line)}')
    print(f'✓ Всего записей в базе: {len(data_dict)}')
    print("="*60)

    # Финальное сохранение
    if len(data_dict) > 0:
        save_backup_copy(data_dict, file_path)
        save_data_incrementally(data_dict, file_path)

    # Обновляем список сломанных ссылок
    if break_line:
        save_broken_urls(break_line)
        print(f"\n✓ Обновлён список сломанных ссылок: {len(break_line)} шт.")
    else:
        # Удаляем файл со сломанными ссылками, если все успешно
        try:
            if os.path.exists(broken_urls_file):
                os.remove(broken_urls_file)
                print(f"\n✓ Все ссылки успешно обработаны! Файл удалён.")
        except:
            pass


def get_data_break():
    """Синхронная обертка для асинхронной функции"""
    asyncio.run(retry_broken_urls_async())


def main():
    print("="*60)
    print("ПАРСЕР KERAMOGRANIT.RU С АСИНХРОННОЙ ОБРАБОТКОЙ")
    print(f"Количество одновременных запросов: {CONCURRENT_REQUESTS}")
    print("="*60 + "\n")

    # 1. Сбор ссылок из каталога
    get_url_tile()

    # 2. Основная обработка всех ссылок
    get_data()

    # 3. Повторная обработка сломанных ссылок
    retry_question = input('\nВы желаете повторить обработку сломанных ссылок? ("1" - Да; "0" - Нет): ')
    if retry_question == "1":
        get_data_break()


if __name__ == '__main__':
    # Примечание: Для работы требуется установить aiohttp:
    # pip install aiohttp

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Прервано пользователем")
    finally:
        finish_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"Затраченное на работу скрипта время: {round(finish_time, 2)} секунд ({round(finish_time/60, 2)} минут)")
        print("="*60)
