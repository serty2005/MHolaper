import gspread
import datetime
from datetime import datetime,timedelta
from gspread.utils import ValidationConditionType
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GoogleSheets:
    def __init__(self, cred_file, sheet_url):
        """Инициализация клиента Google Sheets."""
        self.sheet_url = sheet_url
        try:
            # Авторизация с использованием JSON-файла
            self.client = gspread.service_account(filename=cred_file)
            logger.debug("Успешная авторизация в Google Sheets API")
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            raise

    def create_sheet_if_not_exists(self, sheet_name):
        """Создает лист, если он не существует."""
        try:
            spreadsheet = self.client.open_by_url(self.sheet_url)
            try:
                sheet = spreadsheet.worksheet(sheet_name)
                logger.debug(f"Лист '{sheet_name}' уже существует")
            except gspread.WorksheetNotFound:
                sheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
                logger.debug(f"Лист '{sheet_name}' успешно создан")
            return sheet
        except Exception as e:
            logger.error(f"Ошибка создания листа: {e}")
            raise

    def get_sheet(self, sheet_name):
        """Получение объекта листа по имени."""
        try:
            # Открываем таблицу по URL и получаем лист по имени
            spreadsheet = self.client.open_by_url(self.sheet_url)
            sheet = spreadsheet.worksheet(sheet_name)
            logger.debug(f"Лист '{sheet_name}' успешно получен")
            return sheet
        except gspread.SpreadsheetNotFound:
            logger.error(f"Таблица не найдена. Убедитесь, что таблица доступна для client_email из cred.json.")
            raise
        except gspread.WorksheetNotFound:
            logger.error(f"Лист '{sheet_name}' не найден в таблице.")
            raise
        except Exception as e:
            logger.error(f"Ошибка получения листа: {e}")
            raise

    def set_date_format(self, sheet_name, cell):
        """Устанавливает формат ячейки как 'Дата"""
        try:
            sheet = self.get_sheet(sheet_name)
            # Устанавливаем формат ячейки как "Дата"
            sheet.format(cell, {"numberFormat": {"type": "DATE"}})
            logger.info(f"Формат ячейки {cell} установлен как 'Дата'")
        except Exception as e:
            logger.error(f"Ошибка установки формата ячейки: {e}")
            raise

    def get_date_from_cell(self, sheet_name, cell):
        """Получает дату из ячейки и преобразует её в формат OLAP."""
        try:
            sheet = self.get_sheet(sheet_name)
            # Получаем значение ячейки
            date_value = sheet.acell(cell).value
            if not date_value:
                raise ValueError(f"Ячейка {cell} пуста")
            
            # Преобразуем значение в объект datetime
            try:
                # Если значение уже в формате строки (например, "2023-01-01")
                date_obj = datetime.strptime(date_value, "%d.%m.%Y")
            except ValueError:
                # Если значение в формате серийного числа (например, 44927)
                date_obj = datetime(1899, 12, 30) + timedelta(days=float(date_value))
            
            # Преобразуем в формат OLAP (2025-02-01T00:00:00)
            olap_date = date_obj.strftime("%Y-%m-%dT00:00:00")
            logger.info(f"Дата из ячейки {cell} преобразована в формат OLAP: {olap_date}")
            return olap_date
        except Exception as e:
            logger.error(f"Ошибка получения даты из ячейки: {e}")
            return None


    def write_presets_to_sheet(self, sheet_name, presets):
        """Записывает имена пресетов в служебный лист."""
        try:
            sheet = self.get_sheet(sheet_name)
            # Очищаем лист перед записью
            sheet.clear()
            # Записываем каждое имя пресета в отдельную ячейку столбца A
            for i, preset in enumerate(presets, start=1):
                sheet.update_cell(i, 1, preset)
            logger.info(f"Имена пресетов записаны в лист '{sheet_name}'")
        except Exception as e:
            logger.error(f"Ошибка записи пресетов: {e}")
            raise

    def create_dropdown_list(self, sheet_name, cell, source_range):
        """Создает раскрывающийся список в указанной ячейке."""
        try:
            sheet = self.get_sheet(sheet_name)
            sheet.add_validation(cell, ValidationConditionType.one_of_list, values=source_range, showCustomUi=True)
            logger.info(f"Раскрывающийся список создан в ячейке {cell} на листе '{sheet_name}'")
        except Exception as e:
            logger.error(f"Ошибка создания раскрывающегося списка: {e}")
            raise

    def read_cell(self, sheet_name, cell):
        """Чтение значения из ячейки."""
        try:
            sheet = self.get_sheet(sheet_name)
            value = sheet.acell(cell).value
            logger.debug(f"Значение из ячейки {cell}: {value}")
            return value
        except Exception as e:
            logger.error(f"Ошибка чтения ячейки: {e}")
            raise

    def read_range(self, sheet_name, range):
        """Чтение значений из диапазона."""
        try:
            sheet = self.get_sheet(sheet_name)
            values = sheet.get(range)
            logger.debug(f"Значения из диапазона {range}: {values}")
            return values
        except Exception as e:
            logger.error(f"Ошибка чтения диапазона: {e}")
            raise

    def write_cell(self, sheet_name, cell, value):
        """Запись значения в ячейку."""
        try:
            sheet = self.get_sheet(sheet_name)
            sheet.update_acell(cell, value)
            logger.info(f"Значение '{value}' записано в ячейку {cell}")
        except Exception as e:
            logger.error(f"Ошибка записи в ячейку: {e}")
            raise

    def write_range(self, sheet_name, range, values):
        """Запись значений в диапазон."""
        try:
            sheet = self.get_sheet(sheet_name)
            sheet.update(range, values)
            logger.info(f"Значения записаны в диапазон {range}")
        except Exception as e:
            logger.error(f"Ошибка записи в диапазон: {e}")
            raise

    def update_cell(self, sheet_name, cell, new_value):
        """Обновление значения в ячейке с логированием старого значения."""
        try:
            sheet = self.get_sheet(sheet_name)
            old_value = sheet.acell(cell).value
            sheet.update_acell(cell, new_value)
            logger.info(f"Ячейка {cell} обновлена. Старое значение: {old_value}, Новое значение: {new_value}")
        except Exception as e:
            logger.error(f"Ошибка обновления ячейки: {e}")
            raise

    def update_range(self, sheet_name, range, new_values):
        """Обновление значений в диапазоне с логированием старых значений."""
        try:
            sheet = self.get_sheet(sheet_name)
            old_values = sheet.get(range)
            sheet.update(range, new_values)
            logger.info(f"Диапазон {range} обновлен. Старые значения: {old_values}, Новые значения: {new_values}")
        except Exception as e:
            logger.error(f"Ошибка обновления диапазона: {e}")
            raise

    def clear_cell(self, sheet_name, cell):
        """Очистка ячейки."""
        try:
            sheet = self.get_sheet(sheet_name)
            sheet.update_acell(cell, "")
            logger.info(f"Ячейка {cell} очищена")
        except Exception as e:
            logger.error(f"Ошибка очистки ячейки: {e}")
            raise

    def clear_range(self, sheet_name, range):
        """Очистка диапазона."""
        try:
            sheet = self.get_sheet(sheet_name)
            sheet.batch_clear([range])
            logger.info(f"Диапазон {range} очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки диапазона: {e}")
            raise

    def write_logs_to_cell(self, sheet_name, cell, logs):
        """Записывает логи в указанную ячейку."""
        try:
            sheet = self.get_sheet(sheet_name)
            # Форматируем логи: первая строка — дата-время запуска, остальные — сообщения
            formatted_logs = "\n".join(logs)
            sheet.update_acell(cell, formatted_logs)
            logger.info(f"Логи записаны в ячейку {cell} на листе '{sheet_name}'")
        except Exception as e:
            logger.error(f"Ошибка записи логов в ячейку: {e}")
            raise
   
    def format_cell(self, sheet_name, cell, format):
        """Изменяет формат ячейки."""
        try:
            sheet = self.get_sheet(sheet_name)
            sheet.format(cell, format)
            logger.info(f"Формат ячейки {cell} изменен на листе '{sheet_name}'")
        except Exception as e:
            logger.error(f"Ошибка изменения формата ячейки: {e}")
            raise