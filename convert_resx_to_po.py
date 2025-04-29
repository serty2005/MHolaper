# convert_resx_to_po.py
import xml.etree.ElementTree as ET
import polib
import os
import argparse
from datetime import datetime

def convert_resx(resx_path, po_path, language_code):
    """Конвертирует .resx файл в .po файл."""
    try:
        tree = ET.parse(resx_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Ошибка парсинга XML файла {resx_path}: {e}")
        return
    except FileNotFoundError:
        print(f"Ошибка: Файл {resx_path} не найден.")
        return

    # Создаем или открываем .po файл
    try:
        if os.path.exists(po_path):
            po = polib.pofile(po_path, encoding='utf-8')
            print(f"Обновление существующего файла: {po_path}")
        else:
            po = polib.POFile(encoding='utf-8')
            po.metadata = {
                'Project-Id-Version': 'MyHoreca OLAPer',
                'Report-Msgid-Bugs-To': '',
                'POT-Creation-Date': datetime.now().strftime('%Y-%m-%d %H:%M+%Z'),
                'PO-Revision-Date': datetime.now().strftime('%Y-%m-%d %H:%M+%Z'),
                'Last-Translator': 'Your Name <your.email@example.com>',
                'Language-Team': f'{language_code.upper()} <your.email@example.com>',
                'Language': language_code,
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=utf-8',
                'Content-Transfer-Encoding': '8bit',
            }
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(po_path), exist_ok=True)
            print(f"Создание нового файла: {po_path}")

    except Exception as e:
        print(f"Ошибка при работе с PO файлом {po_path}: {e}")
        return

    added_count = 0
    updated_count = 0

    # Ищем все элементы <data>
    for data_elem in root.findall('.//data'):
        name = data_elem.get('name')
        value_elem = data_elem.find('value')

        if name and value_elem is not None and value_elem.text:
            msgid = name
            msgstr = value_elem.text.strip()

            # Ищем существующую запись или создаем новую
            entry = po.find(msgid)
            if entry:
                if entry.msgstr != msgstr:
                    entry.msgstr = msgstr
                    # Можно добавить флаг 'fuzzy' для проверки вручную, если нужно
                    # entry.flags.append('fuzzy')
                    updated_count +=1
            else:
                entry = polib.POEntry(
                    msgid=msgid,
                    msgstr=msgstr
                    # occurrence=[(resx_path, '')] # Можно добавить информацию об источнике
                )
                po.append(entry)
                added_count += 1
        else:
             print(f"Пропуск некорректной записи: name={name}")

    try:
        po.save(po_path)
        print(f"Конвертация завершена. Добавлено: {added_count}, Обновлено: {updated_count} записей в {po_path}")
    except Exception as e:
        print(f"Ошибка сохранения PO файла {po_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Конвертировать .resx в .po')
    parser.add_argument('resx_file', help='Путь к входному .resx файлу')
    parser.add_argument('po_file', help='Путь к выходному .po файлу')
    parser.add_argument('language', help='Код языка (например, ru)')
    args = parser.parse_args()

    convert_resx(args.resx_file, args.po_file, args.language)

# --- Пример использования из командной строки ---
# python convert_resx_to_po.py static/RestoOlapResources.resx translations/ru/LC_MESSAGES/messages.po ru