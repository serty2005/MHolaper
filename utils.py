import json
import logging
from jinja2 import Template
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)
# Уровень логирования уже должен быть настроен в app.py или основном модуле
# logger.setLevel(logging.DEBUG) # Можно убрать, если настраивается глобально

# Функция load_temps удалена, так как пресеты загружаются из API RMS


def generate_template_from_preset(preset):
    """
    Генерирует один шаблон запроса OLAP на основе пресета,
    подставляя плейсхолдеры для дат в соответствующий фильтр.

    Args:
        preset (dict): Словарь с пресетом OLAP-отчета из API RMS.

    Returns:
        dict: Словарь, представляющий шаблон запроса OLAP, готовый для рендеринга.
              Возвращает None, если входной preset некорректен.

    Raises:
        ValueError: Если preset не является словарем или не содержит необходимых ключей.
        Exception: Другие непредвиденные ошибки при обработке.
    """
    if not isinstance(preset, dict):
        logger.error("Ошибка генерации шаблона: входной 'preset' не является словарем.")
        raise ValueError("Preset должен быть словарем.")
    if not all(k in preset for k in ["reportType", "groupByRowFields", "aggregateFields", "filters"]):
         logger.error(f"Ошибка генерации шаблона: пресет {preset.get('id', 'N/A')} не содержит всех необходимых ключей.")
         raise ValueError("Пресет не содержит необходимых ключей (reportType, groupByRowFields, aggregateFields, filters).")

    try:
        # Копируем основные поля из пресета
        template = {
            "reportType": preset["reportType"],
            "groupByRowFields": preset.get("groupByRowFields", []), # Используем get для необязательных полей
            "aggregateFields": preset.get("aggregateFields", []),
            "filters": preset.get("filters", {}) # Работаем с копией фильтров
        }

        # --- Обработка фильтров дат ---
        # Создаем копию словаря фильтров, чтобы безопасно удалять элементы
        current_filters = dict(template.get("filters", {})) # Используем get с default
        filters_to_remove = []
        date_filter_found_and_modified = False

        # Сначала найдем и удалим все существующие фильтры типа DateRange
        for key, value in current_filters.items():
            if isinstance(value, dict) and value.get("filterType") == "DateRange":
                filters_to_remove.append(key)

        for key in filters_to_remove:
            del current_filters[key]
            logger.debug(f"Удален существующий DateRange фильтр '{key}' из пресета {preset.get('id', 'N/A')}.")

        # Теперь добавляем правильный фильтр дат в зависимости от типа отчета
        report_type = template["reportType"]

        if report_type in ["SALES", "DELIVERIES"]:
            # Для отчетов SALES и DELIVERIES используем "OpenDate.Typed"
            # См. https://ru.iiko.help/articles/api-documentations/olap-2/a/h3__951638809
            date_filter_key = "OpenDate.Typed"
            logger.debug(f"Для отчета {report_type} ({preset.get('id', 'N/A')}) будет использован фильтр '{date_filter_key}'.")
            current_filters[date_filter_key] = {
                "filterType": "DateRange",
                "from": "{{ from_date }}",
                "to": "{{ to_date }}",
                "includeLow": True,
                "includeHigh": True
            }
            date_filter_found_and_modified = True # Считаем, что мы успешно добавили нужный фильтр

        elif report_type == "TRANSACTIONS":
            # Для отчетов по проводкам (TRANSACTIONS) используем "DateTime.DateTyped"
            # См. комментарий пользователя и общие практики iiko API
            date_filter_key = "DateTime.DateTyped"
            logger.debug(f"Для отчета {report_type} ({preset.get('id', 'N/A')}) будет использован фильтр '{date_filter_key}'.")
            current_filters[date_filter_key] = {
                "filterType": "DateRange",
                "from": "{{ from_date }}",
                "to": "{{ to_date }}",
                "includeLow": True,
                "includeHigh": True
            }
            date_filter_found_and_modified = True # Считаем, что мы успешно добавили нужный фильтр

        else:
            # Для ВСЕХ ОСТАЛЬНЫХ типов отчетов:
            # Пытаемся найти *любой* ключ, который может содержать дату (логика по умолчанию).
            # Это менее надежно, чем явное указание ключей для SALES/DELIVERIES/TRANSACTIONS.
            # Если в пресете для других типов отчетов нет стандартного поля даты,
            # или оно называется иначе, этот блок может не сработать корректно.
            # Мы уже удалили все DateRange фильтры. Если для этого типа отчета
            # нужен был какой-то специфический DateRange фильтр, он был удален.
            # Это потенциальная проблема, если неизвестные типы отчетов полагаются
            # на предопределенные DateRange фильтры с другими ключами.
            # Пока оставляем так: если тип отчета неизвестен, DateRange фильтр не добавляется.
            logger.warning(f"Для неизвестного типа отчета '{report_type}' ({preset.get('id', 'N/A')}) не удалось автоматически определить стандартный ключ фильтра даты. "
                           f"Фильтр по дате не будет добавлен автоматически. Если он нужен, пресет должен содержать его с другим filterType или его нужно добавить вручную.")
            # В этом случае date_filter_found_and_modified останется False

        # Обновляем фильтры в шаблоне
        template["filters"] = current_filters

        # Логируем результат
        if date_filter_found_and_modified:
             logger.info(f"Шаблон для пресета {preset.get('id', 'N/A')} ('{preset.get('name', '')}') успешно сгенерирован с фильтром даты.")
        else:
             logger.warning(f"Шаблон для пресета {preset.get('id', 'N/A')} ('{preset.get('name', '')}') сгенерирован, но фильтр даты не был добавлен/модифицирован (тип отчета: {report_type}).")

        return template

    except Exception as e:
        logger.error(f"Непредвиденная ошибка при генерации шаблона из пресета {preset.get('id', 'N/A')}: {str(e)}", exc_info=True)
        raise # Перевыбрасываем ошибку


def render_temp(template_dict, context):
    """
    Рендерит шаблон (представленный словарем) с использованием Jinja2.

    Args:
        template_dict (dict): Словарь, представляющий шаблон OLAP-запроса.
        context (dict): Словарь с переменными для рендеринга (например, {'from_date': '...', 'to_date': '...'}).

    Returns:
        dict: Словарь с отрендеренным OLAP-запросом.

    Raises:
        Exception: Ошибки при рендеринге или парсинге JSON.
    """
    try:
        # Преобразуем словарь шаблона в строку JSON для Jinja
        template_str = json.dumps(template_dict)

        # Рендерим строку с помощью Jinja
        rendered_str = Template(template_str).render(context)

        # Преобразуем отрендеренную строку обратно в словарь Python
        rendered_dict = json.loads(rendered_str)

        logger.info('Шаблон OLAP-запроса успешно отрендерен.')
        return rendered_dict
    except Exception as e:
        logger.error(f"Ошибка рендеринга шаблона: {str(e)}", exc_info=True)
        raise


def get_dates(start_date, end_date):
    """
    Проверяет даты на корректность и формат YYYY-MM-DD.

    Args:
        start_date (str): Дата начала в формате 'YYYY-MM-DD'.
        end_date (str): Дата окончания в формате 'YYYY-MM-DD'.

    Returns:
        tuple: Кортеж (start_date, end_date), если даты корректны.

    Raises:
        ValueError: Если формат дат некорректен или дата начала позже даты окончания.
    """
    date_format = "%Y-%m-%d"
    try:
        start = datetime.strptime(start_date, date_format)
        end = datetime.strptime(end_date, date_format)
    except ValueError:
        logger.error(f"Некорректный формат дат: start='{start_date}', end='{end_date}'. Ожидается YYYY-MM-DD.")
        raise ValueError("Некорректный формат даты. Используйте YYYY-MM-DD.")

    if start > end:
        logger.error(f"Дата начала '{start_date}' не может быть позже даты окончания '{end_date}'.")
        raise ValueError("Дата начала не может быть позже даты окончания.")

    return start_date, end_date