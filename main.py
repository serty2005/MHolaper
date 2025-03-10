import logging
from request_module import ReqModule
from utils import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == '__main__':

    templates = load_templates()
    reqs = ReqModule()

    try:
        if reqs.login():
            
            generate_templates(reqs.take_presets())

            report_id = "fdcc7e23-377a-42a1-84de-9a68315d0e66"
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
