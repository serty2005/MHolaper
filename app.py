import json
from flask import Flask, render_template, request, redirect, url_for, flash, g, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import logging
from werkzeug.utils import secure_filename
import shutil

from google_sheets import GoogleSheets
from request_module import ReqModule
from utils import *
from models import db, User, UserConfig


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '994525')
DATA_DIR = os.environ.get('DATA_DIR', '/app/data')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{DATA_DIR}/app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

os.makedirs(DATA_DIR, exist_ok=True)

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to 'login' view if user tries to access protected page

@login_manager.user_loader
def load_user(user_id):
    """Loads user from DB for session management."""
    return db.session.get(User, int(user_id))

# --- Logging Configuration ---
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Helper Functions ---
def get_user_config():
    """Gets the config for the currently logged-in user, creating if it doesn't exist."""
    if not current_user.is_authenticated:
        return None # Or return a default empty config object if preferred for anonymous users
    config = UserConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.session.add(config)
        # Commit immediately or defer, depending on workflow
        # db.session.commit() # Let's commit when saving changes
        logger.info(f"Created new UserConfig for user {current_user.id}")
    return config

def get_user_upload_path(filename=""):
    """Gets the upload path for the current user."""
    if not current_user.is_authenticated:
        return None # Or raise an error
    user_dir = os.path.join(DATA_DIR, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, secure_filename(filename))


rms_config = {}
google_config = {}
presets = []
sheets = []
mappings = []

@app.before_request
def load_user_specific_data():
    """Load user-specific data into Flask's 'g' object for the current request context."""
    g.user_config = None
    if current_user.is_authenticated:
        g.user_config = get_user_config()
        # You could preload other user-specific things here if needed
        # g.presets = g.user_config.presets # Example
        # g.sheets = g.user_config.sheets # Example
        # g.mappings = g.user_config.mappings # Example
    else:
        # Define defaults for anonymous users if necessary
        # g.presets = []
        # g.sheets = []
        # g.mappings = {}
        pass

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        login_user(user, remember=request.form.get('remember'))
        flash('Login successful!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
             flash('Username and password are required.', 'error')
             return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        user_config = UserConfig()
        user.config = user_config
        db.session.add(user)
        # Create associated config immediately
        try:
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            logger.info(f"User '{username}' registered successfully.")
            return redirect(url_for('login'))
        except Exception as e:
             db.session.rollback()
             logger.error(f"Error during registration for {username}: {e}")
             flash('An error occurred during registration. Please try again.', 'error')
             return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/')
@login_required
def index():
    """Главная страница."""
    config = g.user_config
    return render_template(
        'index.html',
        rms_config=config.get_rms_dict(),
        google_config=config.get_google_dict(),
        presets=config.presets,
        sheets=config.sheets,
        mappings=config.mappings,
        client_email=config.google_client_email
    )

@app.route('/configure_rms', methods=['POST'])
@login_required
def configure_rms():
    """Настройка параметров RMS-сервера."""
    config = g.user_config
    try:
        # Логируем вызов функции и параметры
        logger.info(f"User {current_user.id}: Вызов configure_rms с параметрами: {request.form}")

        host = request.form.get('host', '').strip()
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '').strip()

        # Проверяем, что все поля заполнены
        if not host or not login or not password:
            flash('All RMS fields must be filled.', 'error')
            return redirect(url_for('index'))

        # Авторизация на RMS-сервере
        req_module = ReqModule(host, login, password)
        if req_module.login():
            presets_data = req_module.take_presets()  # Сохраняем пресеты в g
            req_module.logout()

            # Обновляем конфигурацию RMS-сервера
            config.rms_host = host
            config.rms_login = login
            config.rms_password = password
            config.presets = presets_data

            db.session.commit()
            flash(f"Successfully authorized on RMS server. Received {len(presets_data)} presets.", 'success')
            logger.info(f"User {current_user.id}: RMS config updated successfully.")
        else:
            flash('Authorization error on RMS server.', 'error')

    except Exception as e:
        db.session.rollback()
        logger.error(f"User {current_user.id}: Ошибка при настройке RMS: {str(e)}")
        flash(f'Error configuring RMS: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/upload_credentials', methods=['POST'])
@login_required
def upload_credentials():
    """Обработчик для загрузки файла credentials для текущего пользователя."""
    config = g.user_config
    if 'cred_file' in request.files:
        cred_file = request.files['cred_file']
        if cred_file.filename != '':
            
            filename = secure_filename(cred_file.filename)
            user_cred_path = get_user_upload_path(filename)

            try:
                # Save the file temporarily first to read it
                temp_path = os.path.join("data", f"temp_{current_user.id}_{filename}") # Temp generic uploads dir
                cred_file.save(temp_path)

                # Извлекаем client_email из JSON-файла
                client_email = None
                with open(temp_path, 'r', encoding='utf-8') as temp_cred_file:
                    cred_data = json.load(temp_cred_file)
                    client_email = cred_data.get('client_email')

                if not client_email:
                     flash('Could not find client_email in the credentials file.', 'error')
                     os.remove(temp_path) # Clean up temp file
                     return redirect(url_for('index'))

                # Move the validated file to the user's persistent directory
                shutil.move(temp_path, user_cred_path)

                # Update config object in DB
                config.google_cred_file_path = user_cred_path
                config.google_client_email = client_email
                # Clear existing sheets list if creds change
                config.sheets = []
                # Optionally clear mappings too?
                # config.mappings = {}

                db.session.commit()
                flash(f'Credentials file successfully uploaded and saved. Email: {client_email}', 'success')
                logger.info(f"User {current_user.id}: Credentials file uploaded to {user_cred_path}")

            except json.JSONDecodeError:
                 flash('Error: Uploaded file is not a valid JSON.', 'error')
                 if os.path.exists(temp_path): os.remove(temp_path) # Clean up temp file
                 logger.warning(f"User {current_user.id}: Uploaded invalid JSON credentials file.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"User {current_user.id}: Ошибка при загрузке credentials: {str(e)}")
                flash(f'Error processing credentials: {str(e)}', 'error')
                if os.path.exists(temp_path): os.remove(temp_path) # Clean up temp file
        else:
            flash('No file was selected.', 'error')
    else:
        flash('Error: Credentials file not found in request.', 'error')

    return redirect(url_for('index'))

@app.route('/configure_google', methods=['POST'])
@login_required
def configure_google():
    """Настройка параметров Google Sheets для текущего пользователя."""
    config = g.user_config
    try:
        logger.info(f"User {current_user.id}: Вызов configure_google с параметрами: {request.form}")

        sheet_url = request.form.get('sheet_url', '').strip()
        if not sheet_url:
            flash('Sheet URL must be provided.', 'error')
            return redirect(url_for('index'))

        # Check if credentials file path exists in config and on disk
        cred_path = config.google_cred_file_path
        if not cred_path or not os.path.isfile(cred_path):
             flash('Please upload a valid credentials file first.', 'warning')
             # Save the URL anyway? Or require creds first? Let's save URL.
             config.google_sheet_url = sheet_url
             config.sheets = [] # Clear sheets if creds are missing/invalid
             # Optionally clear mappings
             # config.mappings = {}
             db.session.commit()
             return redirect(url_for('index'))

        # Update sheet URL in config
        config.google_sheet_url = sheet_url

        # Подключение к Google Sheets
        gs_client = GoogleSheets(cred_path, sheet_url) # Use path from user config
        sheets_data = gs_client.get_sheets()

        # Update sheets list in config
        config.sheets = sheets_data

        # Optionally clear mappings when sheet URL or creds change?
        # config.mappings = {}

        db.session.commit()
        flash(f'Successfully connected to Google Sheets. Found {len(sheets_data)} sheets. Settings saved.', 'success')
        logger.info(f"User {current_user.id}: Google Sheets config updated. URL: {sheet_url}")

    except Exception as e:
        db.session.rollback()
        # Don't clear sheets list on temporary connection error
        logger.error(f"User {current_user.id}: Ошибка при настройке Google Sheets: {str(e)}")
        flash(f'Error connecting to Google Sheets: {str(e)}. Check the URL and service account permissions.', 'error')
        # Still save the URL entered by the user
        config.google_sheet_url = sheet_url
        try:
            db.session.commit()
        except Exception as commit_err:
            logger.error(f"User {current_user.id}: Error committing Google Sheet URL after connection error: {commit_err}")
            db.session.rollback()


    return redirect(url_for('index'))

@app.route('/mapping_set', methods=['POST'])
@login_required
def mapping_set():
    """Обновление сопоставлений листов и отчетов для текущего пользователя."""
    config = g.user_config
    try:
        logger.info(f"User {current_user.id}: Вызов mapping_set с параметрами: {request.form}")

        new_mappings = {}
        # Use sheets stored in the user's config for iteration
        for sheet in config.sheets:
            report_key = f"sheet_{sheet['id']}"
            selected_report_id = request.form.get(report_key)
            if selected_report_id: # Only store non-empty selections
                # Store mapping using sheet title as key, report ID as value
                new_mappings[sheet['title']] = selected_report_id
            # else: # Handle case where user unselects a mapping
                # If sheet title existed in old mappings, remove it? Or keep structure?
                # Keeping it simple: only store active mappings from the form.

        config.mappings = new_mappings # Use the setter
        db.session.commit()

        flash('Mappings updated successfully.', 'success')
        logger.info(f"User {current_user.id}: Mappings updated: {new_mappings}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"User {current_user.id}: Ошибка при обновлении сопоставлений: {str(e)}")
        flash(f'Error updating mappings: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/render_olap', methods=['POST'])
@login_required
def render_olap():
    """Отрисовка данных отчета на листе для текущего пользователя."""
    config = g.user_config
    # Инициализируем переменные заранее
    sheet_title = None
    report_id = None
    preset = None
    req_module = None # Для finally блока

    try:
        # Валидация дат
        from_date, to_date = get_dates(request.form.get('start_date'), request.form.get('end_date'))

        # Получаем имя листа из кнопки
        sheet_title = next((key for key in request.form if key.startswith('render_')), '').replace('render_', '')
        if not sheet_title:
            flash('Error: Could not determine the sheet for rendering the report.', 'error')
            return redirect(url_for('index'))

        logger.info(f"User {current_user.id}: Attempting to render OLAP for sheet '{sheet_title}'")

        # --- Получаем данные из конфига пользователя ---
        report_id = config.mappings.get(sheet_title)
        rms_host = config.rms_host
        rms_login = config.rms_login
        rms_password = config.rms_password # Decrypted via property getter
        cred_path = config.google_cred_file_path
        sheet_url = config.google_sheet_url
        all_presets = config.presets

        # --- Проверки ---
        if not report_id:
            flash(f"Error: No report mapped for sheet '{sheet_title}'.", 'error')
            return redirect(url_for('index'))
        if not all([rms_host, rms_login, rms_password]):
             flash('Error: RMS configuration is incomplete.', 'error')
             return redirect(url_for('index'))
        if not cred_path or not sheet_url or not os.path.isfile(cred_path):
             flash('Error: Google Sheets configuration is incomplete or credentials file is unavailable.', 'error')
             return redirect(url_for('index'))

        preset = next((p for p in all_presets if p['id'] == report_id), None)
        if not preset:
             flash(f"Error: Preset with ID '{report_id}' not found in the saved configuration.", 'error')
             logger.warning(f"User {current_user.id}: Preset ID '{report_id}' not found in stored presets for sheet '{sheet_title}'")
             return redirect(url_for('index'))

        template = generate_temps(presets=[preset])
        if not template:
            flash(f"Error: Failed to generate template for report '{preset.get('name', report_id)}'.", 'error')
            return redirect(url_for('index'))

        context = {"from_date": from_date, "to_date": to_date}
        json_body = render_temps(template, context)

        # --- Инициализация модулей ---
        req_module = ReqModule(rms_host, rms_login, rms_password)
        # Инициализируем GoogleSheets *перед* блоком finally, чтобы иметь доступ в случае ошибки API
        gs_client = GoogleSheets(cred_path, sheet_url) # Обработка ошибок инициализации уже внутри __init__

        # --- Выполняем запросы ---
        if req_module.login():
            try:
                logger.info(f"User {current_user.id}: Sending OLAP request for report {report_id} ({preset.get('name', '')})")
                result = req_module.take_olap(json_body)
                logger.debug(f"User {current_user.id}: OLAP result received (first 50 chars): {str(result)[:50]}...")

                # Обрабатываем данные
                if 'data' in result and isinstance(result['data'], list):
                    # Преобразуем данные: Заголовки + Строки
                    headers = []
                    data_to_insert = [] # Итоговый список списков для Google Sheets

                    if result['data']:
                        # Получаем заголовки из первого элемента, сохраняя порядок ключей Python 3.7+
                        headers = list(result['data'][0].keys())
                        data_to_insert.append(headers) # Добавляем строку заголовков

                        for item in result['data']:
                            # Формируем строку в соответствии с порядком заголовков
                            row = [item.get(h, '') for h in headers] # Обрабатываем отсутствующие ключи
                            data_to_insert.append(row)
                    else:
                         logger.warning(f"User {current_user.id}: OLAP report {report_id} returned no data.")
                         # Данных нет, просто очистим лист и сообщим пользователю

                    # --- ИСПОЛЬЗУЕМ НОВЫЙ МЕТОД ИЗ GOOGLE_SHEETS.PY ---
                    try:
                        # Метод сам очистит лист и запишет данные (или только очистит, если data_to_insert пуст после заголовков)
                        gs_client.clear_and_write_data(sheet_title, data_to_insert, start_cell="A1") # Указываем начальную ячейку

                        if len(data_to_insert) > 1 : # Проверяем, были ли записаны строки данных (кроме заголовка)
                            flash(f"Report data '{preset.get('name', report_id)}' successfully written to sheet '{sheet_title}'.", 'success')
                        else:
                             flash(f"Report '{preset.get('name', report_id)}' returned no data for the specified period. Sheet '{sheet_title}' cleared.", 'warning')

                    except Exception as gs_error: # Ловим ошибки конкретно от Google Sheets операции
                         logger.error(f"User {current_user.id}: Failed to write data to Google Sheet '{sheet_title}'. Error: {gs_error}", exc_info=True)
                         flash(f"User {current_user.id}: Failed to write data to Google Sheet '{sheet_title}'. Error: {gs_error}", 'error')
                         # Не перенаправляем здесь, чтобы пользователь видел ошибку, возможно, RMS данные были получены

                else:
                     logger.error(f"User {current_user.id}: OLAP response format unexpected: {result}")
                     flash(f"Error: Unexpected response format from RMS for report '{preset.get('name', report_id)}'.", 'error')

            # except gspread.exceptions.APIError as api_err: # Можно ловить специфичные ошибки Google API здесь
            #      logger.error(f"User {current_user.id}: Google API error during report processing: {api_err}", exc_info=True)
            #      flash(f"Ошибка Google API при обработке листа '{sheet_title}': {api_err}", 'error')
            except Exception as report_err: # Общий обработчик ошибок во время получения/записи отчета
                logger.error(f"User {current_user.id}: Ошибка при получении/записи отчета {report_id}: {report_err}", exc_info=True)
                flash(f"Error fetching/writing report '{preset.get('name', report_id)}': {report_err}", 'error')
            finally:
                 # Убедимся, что выходим из сессии RMS, даже если была ошибка с Google Sheets
                 if req_module and req_module.token: # Проверяем, что req_module был создан и есть токен
                    req_module.logout()
        else:
            flash('Authorization error on RMS server when trying to fetch the report.', 'error')

    except ValueError as ve: # Ошибка валидации дат
        flash(f'Date error: {str(ve)}', 'error')
        logger.warning(f"User {current_user.id}: Date validation error: {ve}")
    except Exception as e:
        # Ловим остальные непредвиденные ошибки (например, ошибки инициализации GoogleSheets, ReqModule, ошибки Jinja и т.д.)
        logger.error(f"User {current_user.id}: Общая ошибка в render_olap для листа '{sheet_title}': {str(e)}", exc_info=True)
        flash(f"An unexpected error occurred: {str(e)}", 'error')
    finally:
         # Дополнительно разлогиниваемся, если ошибка произошла до блока finally внутри 'if req_module.login()'
         if req_module and req_module.token:
             try:
                 req_module.logout()
             except Exception as logout_err:
                 logger.warning(f"User {current_user.id}: Error during final logout attempt: {logout_err}")


    return redirect(url_for('index'))


# --- Command Line Interface for DB Management ---
# Run 'flask db init' first time
# Run 'flask db migrate -m "Some description"' after changing models
# Run 'flask db upgrade' to apply migrations

@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables."""
    db.create_all()
    print('Initialized the database.')

# --- Main Execution ---
if __name__ == '__main__':
    # Ensure the database exists before running
    with app.app_context():
         db.create_all() # Create tables if they don't exist
    # Run Flask app
    # Set debug=False for production!
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 5005))) # Listen on all interfaces if needed