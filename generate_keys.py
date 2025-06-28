import os
import base64
from cryptography.fernet import Fernet

# Generate a strong SECRET_KEY for Flask
# Using 24 random bytes, converted to hex (results in a 48-char string)
flask_secret_key = os.urandom(24).hex()

# Generate a strong ENCRYPTION_KEY for Fernet
# This generates a key in the correct base64 format (32 bytes -> 44 base64 chars)
fernet_encryption_key = Fernet.generate_key().decode()

print("Generated SECRET_KEY (for Flask):")
print(flask_secret_key)
print("-" * 30)
print("Generated ENCRYPTION_KEY (for RMS password encryption):")
print(fernet_encryption_key)
print("-" * 30)
print("IMPORTANT:")
print("1. Keep these keys SECRET and do NOT commit them to version control.")
print("2. Set these as environment variables SECRET_KEY and ENCRYPTION_KEY when running your application.")
print("3. The ENCRYPTION_KEY MUST remain CONSTANT for your application to be able to decrypt previously saved RMS passwords.")