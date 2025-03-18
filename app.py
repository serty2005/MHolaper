import json
from flask import Flask, render_template, request, redirect, url_for, flash
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

@app.route('/')
def index():
    try:
        with open('uploads/config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
            global rms_config, google_config, mappings
            rms_config = config.get('rms', {})
            google_config = config.get('google', {})
            mappings = config.get('mappings', {})

    except FileNotFoundError:
        # Создаем базовый конфиг, если файла нет
        base_config = {
            "rms": {},
            "google": {},
            "mappings": {}
        }
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump(base_config, file, ensure_ascii=False, indent=4)
        
        # Возвращаем пустые конфигурации

    return render_template('index.html', rms_config=rms_config, google_config=google_config, presets=presets, sheets=sheets)

@app.route('/configure_rms', methods=['POST'])
def configure_rms():
    """Настройка параметров RMS-сервера."""
    try:
        # Логируем вызов функции и параметры
        logger.info(f"Вызов configure_rms с параметрами: {request.form}")

        # Получаем данные из файла config.json
        with open('uploads/config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)

        global rms_config
        rms_config = config.get('rms', {})

        # Получаем данные из формы
        rms_config['host'] = request.form.get('host', '').strip()
        rms_config['login'] = request.form.get('login', '').strip()
        rms_config['password'] = request.form.get('password', '').strip()

        # Проверяем, что все поля заполнены
        if not rms_config['host'] or not rms_config['login'] or not rms_config['password']:
            flash('Все поля должны быть заполнены', 'error')
            return redirect(url_for('index'))

        # Авторизация на RMS-сервере
        req_module = ReqModule(rms_config['host'], rms_config['login'], rms_config['password'])
        if req_module.login():
            global presets
            presets = req_module.take_presets()  # Сохраняем пресеты
            generate_temps(presets)
            req_module.logout()
            flash(f"Успешная авторизация на RMS-сервере. Получено {len(presets)} пресетов", 'success')
        else:
            flash('Ошибка авторизации на RMS-сервере', 'error')

        # Сохраняем обновленные данные обратно в файл
        config['rms'] = rms_config
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)

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

        # Проверяем, что файл был загружен
        if 'cred_file' not in request.files:
            flash('Файл не был загружен', 'error')
            return redirect(url_for('index'))

        cred_file = request.files['cred_file']
        if cred_file.filename == '':
            # Если файл не выбран, используем существующий файл из конфига
            with open('uploads/config.json', 'r', encoding='utf-8') as file:
                config = json.load(file)
                global google_config
                google_config = config.get('google', {})
                cred_file_path = google_config.get('cred_file')
        else:
            # Сохраняем новый файл
            cred_file_path = os.path.join("uploads", cred_file.filename)
            cred_file.save(cred_file_path)

        # Проверяем, что URL таблицы был введен
        sheet_url = request.form.get('sheet_url', '').strip()
        if not sheet_url:
            flash('URL таблицы должен быть заполнен', 'error')
            return redirect(url_for('index'))

        # Обновляем конфиг
        with open('uploads/config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)

        config['google'] = {
            'cred_file': cred_file_path,
            'sheet_url': sheet_url
        }

        # Сохраняем обновленный конфиг
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)

        # Подключение к Google Sheets
        gs_client = GoogleSheets(cred_file_path, sheet_url)
        global sheets
        sheets = gs_client.get_sheets()  # Получаем список листов
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

        # Подставляем сохраненные сопоставления
        with open('uploads/config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)

        # Обновляем сопоставления
        global mappings
        global sheets
        mappings = config.get('mappings', {})

        for sheet in sheets:
            report_key = f"report_{sheet['title']}"
            if report_key in request.form:
                mappings[sheet['title']] = request.form[report_key]

        
        with open('uploads/config.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)


        flash('Сопоставления успешно обновлены', 'success')
    except Exception as e:
        logger.error(f"Ошибка при обновлении сопоставлений: {str(e)}")
        flash(f'Ошибка при обновлении сопоставлений: {str(e)}', 'error')

    return redirect(url_for('index'))


if __name__ == '__main__':

    # Запуск Flask-приложения
    app.run(debug=True)