generate_keys.py -- генератор ключей для fernet и flask   
После <code>docker build -t mholaper .</code>    
при запуске контейнера ожидаются 2 переменные 
SECRET_KEY="ключ для Flask" --- можно любой   
ENCRYPTION_KEY="ключ для Fernet" --- генерируется вызовом <code>Fernet.generate_key().decode()</code>   
Проще запустить модуль и получить оба ключа нормальной сложности.   
Пример строки для запуска контейнера   
<code>docker run -d -p 5005:5005 -e SECRET_KEY="52f332312321e718fcc7d8f89cec84df9d84bb7b1" -e ENCRYPTION_KEY="4kjMqo213123211123oeLOjR6vYHVzLJCzDjobT6Y=" mholaper</code>
