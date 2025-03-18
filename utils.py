import json, os
import logging
from jinja2 import Template
import time

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def load_temps(file_path='templates.json'):
    """Загружает шаблоны запросов из JSON-файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            templates = json.load(file)
            logger.info(f'Шаблоны успешно загружены из файла {file_path}')
            return templates
    except Exception as e:
        logger.error(f'Ошибка загрузки шаблонов: {str(e)}')
        raise

def generate_temps(presets, file_path='templates.json'):
    """Генерация шаблонов из полученных OLAP-пресетов"""
    try:
        templates = {}
        for preset in presets:
            template = {
                "reportType": preset["reportType"],
                "groupByRowFields": preset["groupByRowFields"],
                "aggregateFields": preset["aggregateFields"],
                "filters": preset["filters"]
            }

            # Для отчетов SALES и DELIVERIES
            if template["reportType"] in ["SALES", "DELIVERIES"]:
                # Удаляем все существующие фильтры с "filterType": "DateRange" https://ru.iiko.help/articles/api-documentations/olap-2/a/h3__951638809
                filters_to_remove = [
                    key for key, value in template["filters"].items()
                    if value.get("filterType") == "DateRange"
                ]
                for key in filters_to_remove:
                    del template["filters"][key]

                # Правим фильтр по дате на "OpenDate.Typed" https://ru.iiko.help/articles/api-documentations/olap-2/a/h3__951638809
                template["filters"]["OpenDate.Typed"] = {
                    "filterType": "DateRange",
                    "from": "{{ from_date }}",
                    "to": "{{ to_date }}",
                    "includeLow": True,
                    "includeHigh": True
                }
            else:
                # Для остальных отчетов обрабатываем существующие фильтры по дате
                for _, filter_value in template["filters"].items():
                    if filter_value.get("filterType") == "DateRange":
                        filter_value["from"] = "{{ from_date }}"
                        filter_value["to"] = "{{ to_date }}"
                        filter_value.pop("periodType", None)  # Убираем поле periodType, если оно есть

            templates[preset["id"]] = template

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(templates, file, ensure_ascii=False, indent=4)
            logger.info(f"Шаблоны успешно сгенерированы в файл {file_path}")
    except Exception as e:
        logger.error(f"Ошибка генерации шаблонов: {str(e)}")
        raise

def render_temps(template, context):
    """Рендерит шаблон с использованием Jinja2."""
    try:
        if isinstance(template, dict):
            template_str = json.dumps(template)
        else:
            template_str = template
    
        rendered = Template(template_str).render(context)
        logger.info('Шаблон сгенерирован')
        return json.loads(rendered)
    except Exception as e:
        logger.error(f"Ошибка генерации шаблона: {str(e)}")
        raise
