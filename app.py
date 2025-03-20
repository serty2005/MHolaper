import json
from flask import Flask, render_template, request, redirect, url_for, flash, g
import os
import logging
from google_sheets import GoogleSheets
from request_module import ReqModule
from utils import *

# Настройка логирования
logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

os.makedirs("uploads", exist_ok=True)

rms_config = {}
google_config = {}
presets = []
sheets = []
mappings = []

@app.before_request
def load_config():
    """Загрузка конфигурации перед каждым запросом."""
    try:
        with open('uploads/config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
            g.rms_config = config.get('rms', {})
            g.google_config = config.get('google', {})
            cred_path = g.google_config.get('cred_file')
            g.client_email = None
            if cred_path and os.path.isfile(cred_path):
                try:
                    with open(cred_path, 'r', encoding='utf-8') as cred_file:
                        cred_data = json.load(cred_file)
                        g.client_email = cred_data.get('client_email')
                except Exception as e:
                    logger.error(f"Ошибка при чтении Google credentials: {str(e)}")
                    g.client_email = None
            g.mappings = config.get('mappings', {})
            g.presets = config.get('presets', [])  # Загружаем пресеты
            g.sheets = config.get('sheets', [])  # Загружаем листы
    except FileNotFoundError:
        g.rms_config = {}
        g.google_config = {}
        g.client_email = None
        g.mappings = {}
        g.presets = []
        g.sheets = []

@app.route('/')
def index():
    """Главная страница."""
    return render_template(
        'index.html',
        rms_config=g.rms_config,
        google_config=g.google_config,
        presets=g.get('presets', []),  # Передача пресетов через g
        sheets=g.get('sheets', []),  # Передача листов через g
        mappings=g.get('mappings', {}),
        client_email=g.client_email
    )

@app.route('/configure_rms', methods=['POST'])
def configure_rms():
    """Настройка параметров RMS-сервера."""
    try:
        # Логируем вызов функции и параметры
        logger.info(f"Вызов configure_rms с параметрами: {request.form}")

        g.rms_config['host'] = request.form.get('host', '').strip()
        g.rms_config['login'] = request.form.get('login', '').strip()
        g.rms_config['password'] = request.form.get('password', '').strip()

        # Проверяем, что все поля заполнены
        if not all(g.rms_config.values()):
            flash('Все поля должны быть заполнены', 'error')
            return redirect(url_for('index'))

        # Авторизация на RMS-сервере
        req_module = ReqModule(g.rms_config['host'], g.rms_config['login'], g.rms_config['password'])
        if req_module.login():
            g.presets = req_module.take_presets()  # Сохраняем пресеты в g
            # generate_temps(g.presets)
            req_module.logout()
            flash(f"Успешная авторизация на RMS-сервере. Получено {len(g.presets)} пресетов", 'success')
        else:
            flash('Ошибка авторизации на RMS-сервере', 'error')

        # Сохраняем обновленные данные обратно в файл
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump({
                'rms': g.rms_config, 
                'google': g.google_config,
                'client_email': g.client_email,
                'sheets': g.sheets,
                'mappings': g.mappings,
                'presets': g.presets
                }, file, ensure_ascii=False, indent=4)

    except Exception as e:
        logger.error(f"Ошибка при настройке RMS: {str(e)}")
        flash(f'Ошибка при настройке RMS: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/configure_google', methods=['POST'])
def configure_google():
    """Настройка параметров Google Sheets."""
    try:
        # Логируем вызов функции и параметры
        logger.info(f"Вызов configure_google с параметрами: {request.form}")

        # Получаем путь к файлу credentials 
        cred_file_path = g.google_config.get('cred_file') 

        # Проверяем, был ли файл загружен через форму
        if 'cred_file' in request.files:
            cred_file = request.files['cred_file']
            if cred_file.filename != '':
                cred_file_path = os.path.join("uploads", cred_file.filename)
                cred_file.save(cred_file_path)
                g.google_config['cred_file'] = cred_file_path
            else:
                flash('Файл не был выбран', 'error')
                return redirect(url_for('index'))
        
        # Проверяем наличие файла по указанному пути
        if not os.path.isfile(cred_file_path): 
            flash(f'Файл не найден по пути: {cred_file_path}', 'error')
            return redirect(url_for('index'))

        # Извлекаем client_email из JSON-файла
        try:
            with open(cred_file_path, 'r', encoding='utf-8') as cred_file:
                cred_data = json.load(cred_file)
                g.client_email = cred_data.get('client_email')
        except Exception as e:
            logger.error(f"Ошибка при извлечении client_email из JSON-файла: {str(e)}")
            flash(f'Ошибка при чтении Google credentials: {str(e)}', 'error')
            return redirect(url_for('index'))

        # Проверяем, что URL таблицы был введен
        sheet_url = request.form.get('sheet_url', '').strip()
        if not sheet_url:
            flash('URL таблицы должен быть заполнен', 'error')
            return redirect(url_for('index'))

        # Обновляем конфиг
        g.google_config['sheet_url'] = sheet_url

        # Подключение к Google Sheets
        gs_client = GoogleSheets(g.google_config['cred_file'], g.google_config['sheet_url'])
        g.sheets = gs_client.get_sheets()  # Сохраняем листы в g
        
        # Сохраняем обновленный конфиг
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump({
                'rms': g.rms_config, 
                'google': g.google_config,
                'client_email': g.client_email,
                'sheets': g.sheets,
                'mappings': g.mappings,
                'presets': g.presets
                }, file, ensure_ascii=False, indent=4)

        flash('Успешное подключение к Google Sheets', 'success')

    except Exception as e:
        logger.error(f"Ошибка при настройке Google Sheets: {str(e)}")
        flash(f'Ошибка при настройке Google Sheets: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/mapping_set', methods=['POST'])
def mapping_set():
    """Обновление сопоставлений листов и отчетов."""
    try:
        # Логируем вызов функции и параметры
        logger.info(f"Вызов mapping_set с параметрами: {request.form}")

        for sheet in g.sheets:
            report_key = f"sheet_{sheet['id']}"
            if report_key in request.form:
                g.mappings[sheet['title']] = request.form[report_key]

        
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump({
                'rms': g.rms_config, 
                'google': g.google_config,
                'client_email': g.client_email,
                'sheets': g.sheets,
                'mappings': g.mappings,
                'presets': g.presets
                }, file, ensure_ascii=False, indent=4)

        flash('Сопоставления успешно обновлены', 'success')
    except Exception as e:
        logger.error(f"Ошибка при обновлении сопоставлений: {str(e)}")
        flash(f'Ошибка при обновлении сопоставлений: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/render_olap', methods=['POST'])
def render_olap():
    """Отрисовка данных отчета на листе."""
    try:
        # Валидация дат
        from_date, to_date = get_dates(request.form.get('start_date'), request.form.get('end_date'))

        # Получаем имя листа, для которого нужно отрисовать отчет
        sheet_title = next((key for key in request.form if key.startswith('render_')), '').replace('render_', '')
        if not sheet_title:
            flash('Ошибка: Не выбран лист для отрисовки отчета', 'error')
            return redirect(url_for('index'))

        # Получаем ID отчета из сопоставлений
        report_id = g.mappings.get(sheet_title)
        if not report_id:
            flash(f"Ошибка: Нет сопоставленного отчета для листа '{sheet_title}'", 'error')
            return redirect(url_for('index'))
        preset = next((preset for preset in g.presets if preset['id'] == report_id), None)
        # Получаем шаблон отчета
        template = generate_temps(presets=[preset])
        if not template:
            flash(f"Ошибка: Шаблон для отчета '{report_id}' не найден", 'error')
            return redirect(url_for('index'))

        # Рендерим шаблон с заданным контекстом (даты)
        context = {"from_date": from_date, "to_date": to_date}
        json_body = render_temps(template, context)

        # Отправляем запрос к RMS API для получения данных отчета
        req_module = ReqModule(g.rms_config['host'], g.rms_config['login'], g.rms_config['password'])
        if req_module.login():
            result = req_module.take_olap(json_body)
            req_module.logout()

            # Обрабатываем полученные данные и записываем их в Google Sheets
            gs_client = GoogleSheets(g.google_config['cred_file'], g.google_config['sheet_url'])
            
            # Предполагаем, что данные отчета имеют формат списка словарей
            data_to_insert = []
            for item in result['data']: 
                row = list(item.values())
                data_to_insert.append(row)
            
            # Очищаем ячейки перед записью (замените 'A5:E' на нужный диапазон)
            # Записываем данные в Google Sheets
            gs_client.write_range(sheet_title, "A1", data_to_insert)

            flash(f"Данные отчета '{report_id}' успешно отрисованы на листе '{sheet_title}'", 'success')
        else:
            flash('Ошибка авторизации на RMS-сервере', 'error')

    except Exception as e:
        logger.error(f"Ошибка при отрисовке данных отчета: {str(e)}")
        flash(f"Ошибка при отрисовке данных отчета: {str(e)}", 'error')

    return redirect(url_for('index'))


if __name__ == '__main__':

    # Запуск Flask-приложения
    app.run(debug=True)