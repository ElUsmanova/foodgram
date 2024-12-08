# Foodgram
**Foodgram** — это веб-приложение для создания, хранения и обмена рецептами. Пользователи могут добавлять свои рецепты, сохранять их в избранное и формировать список покупок.
Зарегестрированные пользователи могут подписываться на авторов рецептов или добавлять рецепты в корзину, в избранное.

## Запуск проекта локально
- Склонировать проект и перейти в папку проекта

```bash
git clone https://github.com/ElUsmanova/foodgram
cd foodgram
```
- Установить и активировать виртуальное окружение

```bash
python3 -m venv venv
source venv\bin\activate
```

- Установить зависимости из файла **requirements.txt**
 
```bash
pip install -r requirements.txt
``` 
- В папке с файлом manage.py выполнить команды:

```bash
python manage.py makemigrations
python manage.py migrate
```
- Создать пользователя с неограниченными правами:

```bash
python manage.py createsuperuser
```

## Docker инструкция

Проект можно развернуть используя контейнеризацию с помощью Docker  
Параметры запуска описаны в `docker-compose.yml`.

- Создать и сохранить переменные окружения в **.env** файл, образец ниже
```bash
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram_exmpl
POSTGRES_USER=user
POSTGRES_PASSWORD=12345
POSTGRES_DB=name #имя БД которое возьмет образ postgres
DB_HOST=db
DB_PORT=5432
```

- Запустить docker-compose

```bash
docker-compose up
```
- Выполнить миграции и подключить статику

```bash
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py collectstatic
```
- Создать superuser

```bash
docker-compose exec backend python manage.py createsuperuser
```
### Автор
Элина Усманова