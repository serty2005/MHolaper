import gspread
import logging

# Настройка логирования
logger = logging.getLogger(__name__)


def log_exceptions(func):
    """Декоратор для логирования исключений."""
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}")
            raise
    return wrapper


class GoogleSheets:
    def __init__(self, cred_file, sheet_url):
        """Инициализация клиента Google Sheets."""
        self.client = gspread.service_account(filename=cred_file)
        self.sheet_url = sheet_url
        self.spreadsheet = self.client.open_by_url(sheet_url)

    def get_sheet(self, sheet_name):
        """Возвращает объект листа по имени."""
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except Exception as e:
            logger.error(f"Ошибка получения листа {sheet_name}: {e}")
            raise

    def get_sheets(self):
        """Получение списка листов в таблице."""
        sheets = self.spreadsheet.worksheets()
        return [{"title": sheet.title, "id": sheet.id} for sheet in sheets]

    @log_exceptions
    def update_cell(self, sheet_name, cell, new_value):
        """Обновляет значение ячейки с логированием старого значения."""
        sheet = self.get_sheet(sheet_name)
        batch = sheet.batch_get([cell])
        old_value = batch[0][0] if batch and batch[0] else None
        sheet.update(cell, [[new_value]])
        logger.info(f"Ячейка {cell} обновлена. Старое: {old_value}, Новое: {new_value}")

    @log_exceptions
    def write_range(self, sheet_name, range, values):
        """Запись значений в диапазон."""
        sheet = self.get_sheet(sheet_name)
        sheet.clear()
        sheet.batch_update([{"range": range, "values": values}])
        logger.info(f"Записаны значения в диапазон {range}")

    @log_exceptions
    def read_range(self, sheet_name, range):
        """Чтение значений из диапазона."""
        sheet = self.get_sheet(sheet_name)
        values = sheet.batch_get([range])[0]  # Читаем данные одним запросом
        logger.debug(f"Значения из диапазона {range}: {values}")
        return values

