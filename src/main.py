import logging
import re
import requests_cache

from urllib.parse import urljoin
from bs4 import BeautifulSoup as BS
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_URL
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BS(response.text, features='lxml')
    get_section = find_tag(soup,
                           'section',
                           attrs={'id': 'what-s-new-in-python'})
    get_div = find_tag(get_section,
                       'div',
                       attrs={'class': "toctree-wrapper compound"})
    get_li = get_div.find_all('li',
                              attrs={'class': "toctree-l2"})
    result = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for li in tqdm(get_li):
        version_a_tag = find_tag(li, 'a')['href']

        ssil = urljoin(whats_new_url, version_a_tag)
        response = get_response(session, ssil)
        if response is None:
            continue
        soup_v = BS(response.text, 'lxml')
        h1 = find_tag(soup_v, 'h1')
        dl = find_tag(soup_v, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        result.append((ssil, h1.text, dl_text))
        return result


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BS(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')
    result = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        result.append((link, version, status))
    return result


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BS(response.text, 'lxml')
    table_tag = find_tag(soup, 'table', {'class': 'docutils'})
    a4_tag = find_tag(table_tag, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    a4_link = a4_tag['href']
    archive_url = urljoin(downloads_url, a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    print(filename)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, PEP_URL)
    if response is None:
        return
    soup = BS(response.text, 'lxml')
    get_section = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    get_table = find_tag(get_section, 'tbody')
    get_rows = get_table.find_all('tr')
    count_dict = {}
    for row in get_rows:
        td_tag = find_tag(row, 'td')
        href_tag = td_tag.find_next_sibling('td')
        td_tag = td_tag.text
        abbr_status = None
        if len(td_tag) == 2:
            abbr_status = td_tag[1]
        link = urljoin(PEP_URL, href_tag.a['href'])
        response = get_response(session, link)
        if response is None:
            continue
        soup = BS(response.text, 'lxml')
        status_element = soup.find('dl',
                                   {'class': 'rfc2822 field-list simple'})
        get_status = status_element.find(string=re.compile(r'^Status$')).parent
        status_tag = get_status.find_next_sibling('dd').text

        if abbr_status is not None and \
           status_tag not in EXPECTED_STATUS[abbr_status]:
            error_msg = f'Не найден статус: {status_tag} в ожидаемых'
            logging.info(error_msg)
            continue
        for abbr, status in EXPECTED_STATUS.items():
            if status_tag in status:
                count_dict[abbr] = count_dict.get(abbr, 0) + 1
    count_dict['Total'] = sum([value for value in count_dict.values()])
    result = [('Статус', 'Количество')]
    result.extend(count_dict.items())
    return result


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep, }


def main():
    configure_logging()
    # Отмечаем в логах момент запуска программы.
    logging.info('Парсер запущен!')
    # Конфигурация парсера аргументов командной строки —
    # передача в функцию допустимых вариантов выбора.
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    # Считывание аргументов из командной строки.
    args = arg_parser.parse_args()
    # Логируем переданные аргументы командной строки.
    logging.info(f'Аргументы командной строки: {args}')
    # Создание кеширующей сессии.
    session = requests_cache.CachedSession()
    # Если был передан ключ '--clear-cache', то args.clear_cache == True.
    if args.clear_cache:
        # Очистка кеша.
        session.cache.clear()
    # Получение из аргументов командной строки нужного режима работы.
    parser_mode = args.mode
    # Поиск и вызов нужной функции по ключу словаря.
    results = MODE_TO_FUNCTION[parser_mode](session)
    # Если из функции вернулись какие-то результаты,
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
