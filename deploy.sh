cp compose/django/requirements.txt Pipfile
pyenv/bin/pip install -r Pipfile

zappa update
rm -rf static
is_zappa=true pyenv/bin/python manage.py collectstatic --noinput
rm -rf static
zappa manage production migrate

