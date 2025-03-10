import json
import logging
from jinja2 import Template

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_templates(file_path='templates.json'):
    """Загружает шаблоны запросов из JSON-файла."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            templates = json.load(file)
            logger.info(f'Шаблоны успешно загружены из файла {file_path}')
            return templates
    except Exception as e:
        logger.error(f'Ошибка загрузки шаблонов: {str(e)}')
        raise

def render_template(template, context):
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