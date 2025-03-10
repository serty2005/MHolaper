import os
import requests
import logging
import hashlib

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные окружения
APP_LOGIN = os.getenv('APP_LOGIN')
app_pass = os.getenv("APP_PASS")
APP_PASSWORD = hashlib.sha1(app_pass.encode('utf-8')).hexdigest()
API_SERVER_URL = os.getenv('SERVER_URL')

class ReqModule:
    def __init__(self):
        self.token = None
        self.session = requests.Session()

    def login(self):
        """Функция для получения токена авторизации.
        Занимает слот лицензии входа в бэкофис"""
        try:
            response = self.session.post(
                f'{API_SERVER_URL}/api/auth',
                data={'login': APP_LOGIN, 'pass': APP_PASSWORD},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            if response.status_code == 200:
                self.token = response.text
                logger.info(f'Получен токен: {self.token}')
                return True
            elif response.status_code == 401:
                logger.error(f'Ошибка авторизации. {response.text}')
                raise Exception('Unauthorized')
        except Exception as e:
            logger.error(f'Error in get_token: {str(e)}')
            raise

    def logout(self):
        """Функция для освобождения токена авторизации."""
        try:
            response = self.session.post(
                f'{API_SERVER_URL}/api/logout',
                data={'key': self.token},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            if response.status_code == 200:
                logger.info(f"{self.token} -- Токен освобожден")
                self.token = None
                return True
        except Exception as e:
            logger.error(f'Ошибка освобождения токена. {str(e)}')
            raise

    def take_olap(self, params):
        """Функция для отправки кастомного OLAP-запроса."""
        try:
            cookies = {'key': self.token}
            response = self.session.post(
                f'{API_SERVER_URL}/api/v2/reports/olap',
                json=params,
                cookies=cookies
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'Не удалось получить кастомный OLAP. Status code: {response.status_code} \nText: {response.text}')
                raise Exception('Request failed')
        except Exception as e:
            logger.error(f'Error in send_olap_request: {str(e)}')
            raise

    def take_presets(self):
        """Функция генерации шаблонов OLAP-запросов"""
        try:
            cookies = {'key': self.token}
            response = self.session.get(
                f'{API_SERVER_URL}/api/v2/reports/olap/presets',
                cookies = cookies
            )
            if response.status_code == 200:
                presets = response.json()
                logger.info('Пресеты переданы в генератор шаблонов')
                return presets
            else:
                logger.error(f"Не удалось получить пресеты. {response.text}")
                raise Exception('Take presets failed')
        except Exception as e:
            logger.error(f'Ошибка получения пресетов: {str(e)}')
            raise