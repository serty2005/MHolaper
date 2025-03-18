import requests
import logging
import hashlib

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ReqModule:
    def __init__(self, host, rmsLogin, password):
        self.host = host
        self.rmsLogin = rmsLogin
        self.password = hashlib.sha1(password.encode('utf-8')).hexdigest()
        self.token = None
        self.session = requests.Session()

    def login(self):
        logger.info(f"Вызов метода login с логином: {self.rmsLogin}")
        try:
            response = self.session.post(
                f'{self.host}/api/auth',
                data={'login': self.rmsLogin, 'pass': self.password},
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
                f'{self.host}/api/logout',
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
                f'{self.host}/api/v2/reports/olap',
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
                f'{self.host}/api/v2/reports/olap/presets',
                cookies=cookies
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