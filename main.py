# import logging
# import time
# from datetime import datetime, timedelta
# from request_module import ReqModule
# from utils import *
# from google_sheets import GoogleSheets
# import os

# # Настройка логирования
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Константы клиента Google Sheets
# SHEET_URL = os.getenv("SHEET_URL")
# CRED_FILE = "cred.json"

# def get_previous_month_dates():
#     """Возвращает первый и последний день прошлого месяца."""
#     today = datetime.now()
#     first_day_of_current_month = today.replace(day=1)
#     last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
#     first_day_of_previous_month = last_day_of_previous_month.replace(day=1)
    
#     # Форматируем даты в строки
#     start_date = first_day_of_previous_month.strftime("%d.%m.%Y")
#     end_date = (last_day_of_previous_month + timedelta(days=1)).strftime("%d.%m.%Y")
    
#     return start_date, end_date

# def main():
#     # Инициализация клиента Google Sheets
#     gs_client = GoogleSheets(CRED_FILE, SHEET_URL)
    
#     # Инициализация модуля запросов
#     reqs = ReqModule()
#     logs = []

#     try:
#         start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         logs.append(f"Запуск программы: {start_time}")

#         if reqs.login():
#             # Шаг 1: Получение всех пресетов отчетов из OLAP-движка
#             presets = reqs.take_presets()
#             logs.append("Пресеты успешно получены")
            
#             # Шаг 1.1: Создание шаблонов из полученных пресетов
#             generate_templates(presets)
#             logs.append("Шаблоны успешно созданы")
        
#             spreadsheet = gs_client.client.open_by_url(SHEET_URL)
#             sheets = spreadsheet.worksheets()
            
#             # Получаем даты по умолчанию
#             default_start_date, default_end_date = get_previous_month_dates()
            
#             for sheet in sheets:
#                 if "main" not in sheet.title.lower():
#                     # Создаем раскрывающийся список в ячейке A1
#                     gs_client.create_dropdown_list(sheet.title, "A1", [preset["name"] for preset in presets])
#                     logs.append(f"Раскрывающийся список создан на листе '{sheet.title}'")

#                     # Устанавливаем формат ячеек для дат
#                     gs_client.set_date_format(sheet.title, "A3")
#                     gs_client.set_date_format(sheet.title, "C3")
#                     logs.append(f"Формат ячейки A3 и C3 установлен для получения даты на листе '{sheet.title}'")
                    
#                     # Устанавливаем значения по умолчанию, если ячейки пусты
#                     current_start_date = gs_client.read_cell(sheet.title, "A3")
#                     current_end_date = gs_client.read_cell(sheet.title, "C3")
                    
#                     if not current_start_date or current_start_date.strip() == "":
#                         gs_client.write_cell(sheet.title, "A3", default_start_date)
#                         logs.append(f"Установлено значение по умолчанию для A3 на листе '{sheet.title}': {default_start_date}")
                    
#                     if not current_end_date or current_end_date.strip() == "":
#                         gs_client.write_cell(sheet.title, "C3", default_end_date)
#                         logs.append(f"Установлено значение по умолчанию для C3 на листе '{sheet.title}': {default_end_date}")
   
#             # Шаг 3: Периодическая проверка ячеек A3 и C3
#             while True:
#                 for sheet in sheets:
#                     if "main" not in sheet.title.lower():
#                         from_date = gs_client.get_date_from_cell(sheet.title, "A3")
#                         to_date = gs_client.get_date_from_cell(sheet.title, "C3")
#                         logs.append(f"Даты на листе '{sheet.title}': from_date={from_date}, to_date={to_date}")

#                         if from_date and to_date:
#                             # Шаг 3.1: Изменение значений на "Принято" и окрашивание в зеленый
#                             gs_client.write_cell(sheet.title, "A3", "Принято")
#                             gs_client.write_cell(sheet.title, "C3", "Принято")
#                             logs.append(f"Даты в листе {sheet.title} приняты")
                            
#                             # Шаг 4: Сопоставление значения из A1 с id шаблона
#                             selected_report = gs_client.read_cell(sheet.title, "A1")
#                             report_id = next((preset["id"] for preset in presets if preset["name"] == selected_report), None)
                            
#                             if report_id:
#                                 # Шаг 5: Запрос отчета по id и вставка периода из п.3
#                                 template = load_templates().get(report_id)
#                                 if template:
#                                     context = {
#                                         "from_date": from_date,
#                                         "to_date": to_date
#                                     }
#                                     json_body = render_template(template, context)
#                                     result = reqs.take_olap(json_body)
#                                     logs.append(f"Отчет {selected_report} успешно получен")
                                    
#                                     # Шаг 6: Вставка данных в таблицу
#                                     data_to_insert = []
#                                     for item in result['data']:
#                                         row = [
#                                             item.get('CashFlowCategory', ''),
#                                             item.get('StartBalance.Money', 0),
#                                             item.get('Sum.Incoming', 0),
#                                             item.get('Sum.Outgoing', 0),
#                                             item.get('FinalBalance.Money', 0)
#                                         ]
#                                         data_to_insert.append(row)
                                    
#                                     gs_client.write_range(sheet.title, "A5", data_to_insert)
#                                     logs.append(f"Данные отчета {selected_report} вставлены в лист {sheet.title}")
                                    
#                                     # Создание словаря для сопоставления названий столбцов
#                                     column_mapping = {
#                                         "CashFlowCategory": "Статья ДДС",
#                                         "StartBalance.Money": "Начальный денежный остаток, Rp",
#                                         "Sum.Incoming": "Сумма прихода, Rp",
#                                         "Sum.Outgoing": "Сумма расхода, Rp",
#                                         "FinalBalance.Money": "Конечный денежный остаток, Rp"
#                                     }
#                                     logs.append(f"Словарь для сопоставления столбцов: {column_mapping}")
#                                 else:
#                                     logs.append(f"Шаблон для отчета {selected_report} не найден")
#                             else:
#                                 logs.append(f"Отчет {selected_report} не найден в пресетах")
                
#                 # Пауза перед следующей проверкой
#                 time.sleep(20)
    
#     except Exception as e:
#         logs.append(f'Ошибка при выполнении программы: {e}')
#     finally:
#         print("\n".join(logs))
#         reqs.logout()

# if __name__ == '__main__':
#     main()