url_group_list = ['https://obi.ru/plitka/plitka-i-keramogranit',
                  'https://obi.ru/santehnika/unitazy-i-instaljacii',
                  'https://obi.ru/santehnika/rakoviny-i-pedestaly']

for url in url_group_list:
    # заходим на страницу группы и собираем количество страниц
    group = url.replace('https://obi.ru/', '').split('/')[0]
    print(group)