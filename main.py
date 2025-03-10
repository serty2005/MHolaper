import logging
from request_module import ReqModule
from utils import load_templates, render_template

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == '__main__':

    templates = load_templates()
    reqs = ReqModule()

    try:
        if reqs.login():

            report_id = "e57ca944-85d7-4db5-8b9a-fe4da55b6fef"
            template = templates.get(report_id)
            if not template:
                raise ValueError("Шаблон не найден в файле templates.json")
            
            context = {
                "from_date": "2025-02-01T00:00:00",
                "to_date": "2025-03-01T00:00:00"
            }

            json_body = render_template(template, context)
            result = reqs.take_olap(json_body)
            logger.info(f'Ответ от сервера: {result}')
    except Exception as e:
        logger.error(f'Ошибка при запросе: {e}')
    finally:
        reqs.logout()
