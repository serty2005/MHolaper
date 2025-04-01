import gspread
import logging
from gspread.utils import rowcol_to_a1

# Настройка логирования
logger = logging.getLogger(__name__)


def log_exceptions(func):
    """Декоратор для логирования исключений."""
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except gspread.exceptions.APIError as e:
            # Логируем специфичные ошибки API Google
            logger.error(f"Google API Error in {func.__name__}: {e.response.status_code} - {e.response.text}")
            raise # Перевыбрасываем, чтобы app.py мог обработать
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


class GoogleSheets:
    def __init__(self, cred_file, sheet_url):
        """Инициализация клиента Google Sheets."""
        try:
            self.client = gspread.service_account(filename=cred_file)
            self.sheet_url = sheet_url
            self.spreadsheet = self.client.open_by_url(sheet_url)
            logger.info(f"Successfully connected to Google Sheet: {self.spreadsheet.title}")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheets client or open sheet {sheet_url}: {e}", exc_info=True)
            raise

    @log_exceptions
    def get_sheet(self, sheet_name):
        """Возвращает объект листа по имени."""
        try:
            sheet = self.spreadsheet.worksheet(sheet_name)
            logger.debug(f"Retrieved worksheet object for '{sheet_name}'")
            return sheet
        except gspread.exceptions.WorksheetNotFound:
             logger.error(f"Worksheet '{sheet_name}' not found in spreadsheet '{self.spreadsheet.title}'.")
             raise
        except Exception:
            raise

    @log_exceptions
    def get_sheets(self):
        """Получение списка листов в таблице."""
        sheets = self.spreadsheet.worksheets()
        sheet_data = [{"title": sheet.title, "id": sheet.id} for sheet in sheets]
        logger.debug(f"Retrieved {len(sheet_data)} sheets: {[s['title'] for s in sheet_data]}")
        return sheet_data

    @log_exceptions
    def update_cell(self, sheet_name, cell, new_value):
        """Обновляет значение ячейки с логированием старого значения."""
        sheet = self.get_sheet(sheet_name)
        # Используем try-except для получения старого значения, т.к. ячейка может быть пустой
        old_value = None
        try:
            old_value = sheet.acell(cell).value
        except Exception as e:
             logger.warning(f"Could not get old value for cell {cell} in sheet {sheet_name}: {e}")

        # gspread рекомендует использовать update для одиночных ячеек тоже
        sheet.update(cell, new_value, value_input_option='USER_ENTERED')
        # Логируем новое значение, т.к. оно могло быть преобразовано Google Sheets
        try:
            logged_new_value = sheet.acell(cell).value
        except Exception:
            logged_new_value = new_value # Fallback if reading back fails

        logger.info(f"Cell {cell} in sheet '{sheet_name}' updated. Old: '{old_value}', New: '{logged_new_value}'")

    @log_exceptions
    def clear_and_write_data(self, sheet_name, data, start_cell="A1"):
        """
        Очищает ВЕСЬ указанный лист и записывает новые данные (список списков),
        начиная с ячейки start_cell.
        """
        if not isinstance(data, list):
             raise TypeError("Data must be a list of lists.")

        sheet = self.get_sheet(sheet_name)

        logger.info(f"Clearing entire sheet '{sheet_name}'...")
        sheet.clear() # Очищаем весь лист
        logger.info(f"Sheet '{sheet_name}' cleared.")

        if not data or not data[0]: # Проверяем, есть ли вообще данные для записи
             logger.warning(f"No data provided to write to sheet '{sheet_name}' after clearing.")
             return # Ничего не записываем, если данных нет

        num_rows = len(data)
        num_cols = len(data[0]) # Предполагаем, что все строки имеют одинаковую длину

        # Рассчитываем конечную ячейку на основе начальной и размеров данных
        try:
             start_row, start_col = gspread.utils.a1_to_rowcol(start_cell)
             end_row = start_row + num_rows - 1
             end_col = start_col + num_cols - 1
             end_cell = rowcol_to_a1(end_row, end_col)
             range_to_write = f"{start_cell}:{end_cell}"
        except Exception as e:
             logger.error(f"Failed to calculate range from start_cell '{start_cell}' and data dimensions ({num_rows}x{num_cols}): {e}. Defaulting to A1 notation if possible.")
             # Фоллбэк на стандартный A1 диапазон, если расчет сломался
             end_cell_simple = rowcol_to_a1(num_rows, num_cols)
             range_to_write = f"A1:{end_cell_simple}"
             if start_cell != "A1":
                 logger.warning(f"Using default range {range_to_write} as calculation from start_cell failed.")


        logger.info(f"Writing {num_rows} rows and {num_cols} columns to sheet '{sheet_name}' in range {range_to_write}...")
        # Используем update для записи всего диапазона одним запросом
        sheet.update(range_to_write, data, value_input_option='USER_ENTERED')
        logger.info(f"Successfully wrote data to sheet '{sheet_name}', range {range_to_write}.")

    @log_exceptions
    def read_range(self, sheet_name, range_a1):
        """Чтение значений из диапазона."""
        sheet = self.get_sheet(sheet_name)
        # batch_get возвращает список списков значений [[...], [...]]
        # Используем get() для более простого чтения диапазона
        values = sheet.get(range_a1)
        # values = sheet.batch_get([range_a1])[0] # batch_get возвращает [[values_for_range1], [values_for_range2], ...]
        logger.debug(f"Read {len(values)} rows from sheet '{sheet_name}', range {range_a1}.")
        # logger.debug(f"Значения из диапазона {range_a1}: {values}") # Может быть слишком много данных для лога
        return values
