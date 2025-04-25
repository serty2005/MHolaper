from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import json
import logging

logger = logging.getLogger(__name__)

db = SQLAlchemy()

# Generate a key for encryption. STORE THIS SECURELY in production (e.g., env variable)
# For development, we can generate/load it from a file.
encryption_key_str = os.environ.get('ENCRYPTION_KEY')
if not encryption_key_str:
    logger.error("ENCRYPTION_KEY environment variable not set! RMS password encryption will fail.")
    # Можно либо упасть с ошибкой, либо использовать временный ключ (НЕ РЕКОМЕНДУЕТСЯ для продакшена)
    # raise ValueError("ENCRYPTION_KEY environment variable is required.")
    # Для локального запуска без установки переменной, можно временно сгенерировать:
    logger.warning("Generating temporary encryption key. SET ENCRYPTION_KEY ENV VAR FOR PRODUCTION!")
    ENCRYPTION_KEY = Fernet.generate_key()
else:
    try:
        ENCRYPTION_KEY = encryption_key_str.encode('utf-8')
        # Простая проверка, что ключ валидный для Fernet
        Fernet(ENCRYPTION_KEY)
        logger.info("Successfully loaded ENCRYPTION_KEY from environment variable.")
    except Exception as e:
         logger.error(f"Invalid ENCRYPTION_KEY format in environment variable: {e}")
         raise ValueError("Invalid ENCRYPTION_KEY format.") from e

fernet = Fernet(ENCRYPTION_KEY)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    config = db.relationship('UserConfig', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class UserConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

    # RMS Config
    rms_host = db.Column(db.String(200))
    rms_login = db.Column(db.String(100))
    rms_password_encrypted = db.Column(db.LargeBinary) # Store encrypted password

    # Google Config
    google_cred_file_path = db.Column(db.String(300)) # Store path, not content
    google_sheet_url = db.Column(db.String(300))
    google_client_email = db.Column(db.String(200)) # Store for display

    # Mappings, Presets, Sheets (Stored as JSON strings)
    mappings_json = db.Column(db.Text, default='{}')
    presets_json = db.Column(db.Text, default='[]')
    sheets_json = db.Column(db.Text, default='[]')

    # --- Helper properties for easy access ---

    @property
    def rms_password(self):
        if self.rms_password_encrypted:
            try:
                return fernet.decrypt(self.rms_password_encrypted).decode('utf-8')
            except Exception: # Handle potential decryption errors
                return None
        return None

    @rms_password.setter
    def rms_password(self, value):
        if value:
            self.rms_password_encrypted = fernet.encrypt(value.encode('utf-8'))
        else:
             self.rms_password_encrypted = None # Or handle as needed

    @property
    def mappings(self):
        return json.loads(self.mappings_json or '{}')

    @mappings.setter
    def mappings(self, value):
        self.mappings_json = json.dumps(value or {}, ensure_ascii=False)

    @property
    def presets(self):
        return json.loads(self.presets_json or '[]')

    @presets.setter
    def presets(self, value):
        self.presets_json = json.dumps(value or [], ensure_ascii=False)

    @property
    def sheets(self):
        return json.loads(self.sheets_json or '[]')

    @sheets.setter
    def sheets(self, value):
        self.sheets_json = json.dumps(value or [], ensure_ascii=False)

    # Convenience getter for template display
    def get_rms_dict(self):
        return {
            'host': self.rms_host or '',
            'login': self.rms_login or '',
            'password': self.rms_password or '' # Use decrypted password here if needed for display/form population (be cautious!)
                                                # Usually, password fields are left blank in forms for security.
        }

    def get_google_dict(self):
         return {
            'cred_file': self.google_cred_file_path or '', # Maybe just indicate if file exists?
            'sheet_url': self.google_sheet_url or ''
         }

    def __repr__(self):
        return f'<UserConfig for User ID {self.user_id}>'