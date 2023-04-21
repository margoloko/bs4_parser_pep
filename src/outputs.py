import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import BASE_DIR, DATETIME_FORMAT


def control_output(results, cli_args):
    """
    Функция управляет выводом результатов парсинга.

    :param results: список списков с результатами парсинга
    :type results: list[list[str]] или list[tuple[str]]
    :param cli_args: объект с аргументами командной строки
    :type cli_args: argparse.Namespace.
    """
    output = cli_args.output
    if output == 'pretty':
        pretty_output(results)
    elif output == 'file':
        file_output(results, cli_args)
    else:
        default_output(results)


def default_output(results):
    """Функция выводит результаты парсинга в консоль."""
    for row in results:
        print(*row)


def pretty_output(results):
    """
    Функция выводит результаты парсинга в виде красивой таблицы.
    """
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    # Добавляем все строки, начиная со второй (с индексом 1).
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    """Функция сохраняет результаты парсинга в файл."""
    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)
    # Получаем режим работы парсера из аргументов командной строки.
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    # Сохраняем текущие дату-время в указанном формате.
    # Результат будет выглядеть вот так: 2021-06-18_07-40-41.
    now_formatted = now.strftime(DATETIME_FORMAT)
    # Собираем имя файла из полученных переменных:
    # «режим работы программы» + «дата и время записи» + формат (.csv).
    file_name = f'{parser_mode}_{now_formatted}.csv'
    # Получаем абсолютный путь к файлу с результатами.
    file_path = results_dir / file_name
    # Через контекстный менеджер открываем файл по сформированному ранее пути
    # в режиме записи 'w', в нужной кодировке utf-8.
    with open(file_path, 'w', encoding='utf-8') as f:
        # Создаём «объект записи» writer.
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)
    logging.info(f'Файл с результатами был сохранён: {file_path}')
