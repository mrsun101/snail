Кратко об http и как работают запросы

Кратко о wsgi в питоне

Потоки данных в нашем ферймворке Request, Response

Будем активно использовать typing

Заводим проект ```ourepictwitter``` в нем папку с нашим фреймоворком ```snail```. 
В папке проекта заводим ```main.py``` в нем пишем
```python
def app(environ, start_response):
        data = b"Hello, World!\n"
        start_response("200 OK", [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(data)))
        ])
        return iter([data])
```
Запускаем Гуникорн через wsl 
```shell script
gunicorn -b 0.0.0.0:8000 main:app
```
и подключаемся через ip адрес http://172.17.12.124:8000/foo?bar=1

Через pprint показываем ```environ```

Переносим ```main.py``` в ```snail``` и импортируем из ```snail/main.py``` в ```main.py``` ```app```

В ```snail/main.py```  ```def app``` переносим в класс Snail

```python
class Snail:

    def __call__(self, environ, start_response, **kwargs):
        data = b"Hello, World!\n"
        start_response("200 OK", [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(data)))
        ])
        return iter([data])
```
а в ```main.py```  пишем
```python
from snail.main import Snail

app = Snail()
```

Начнем с роутинга, добавим ```urls.py``` в ней создадим пустой список ```urlpatterns = []```. Теперь опишем скелет 
фреймворка. А именно создадим несколько файлов
```
snail/exceptions.py  # Исключения
snail/middleware.py  # Промежуточные слои
snail/request.py  # Класс реквеста
snail/response.py  # Класс ответа
snail/urls.py  # Махинация с урлами
snail/view.py  # Вьюхи
```
Сделаем нашу первую вьюху, она пока будет отдаваться по всем урлам, и по сути повторяет ```def app```. 
Начнем с того что определим базовый класс вьюх в ```snail/view.py```
```python
class View:

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs) :
        pass
```
В папке с проектом создадим ```views.py``` и напишем. Пока возвращаем просто текст.

```python
from snail.view import View

class Homepage(View):

    def get(self, request, *args, **kwargs):
        return 'hello world from view!' 
```
Работу с урлами и сделаем чтобы наша страница отдавалась по кореновму пути ```/```

В ```snail/urls.py``` определим датакасс через который мы будем определять урлы в urlpatterns
```python
from dataclasses import dataclass
from snail.view import View
from typing import Type

@dataclass
class Url:
    url: str
    view: Type[View]
```
И пропишем в ```urls.py```
```python
from snail.urls import Url
from views import Homepage


urlpatterns = [
    Url('^$', Homepage),
]
```
Теперь логика работы с урлами, регулярные выражения, пока просто ```snail.main.Snail``` 
добавим ```init``` в котором будем применять урлы и измениним ```main.py```
```python
from snail.urls import Url
from typing import List

class Snail:

    __slots__ = 'urls',

    def __init__(self, urls: List[Url]):
        self.urls = urls


    def __call__(self, environ, start_response, **kwargs):
        data = b"Hello, World!\n"
        start_response("200 OK", [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(data)))
        ])
        return iter([data])

```
```python
from snail.main import Snail
from urls import urlpatterns

app = Snail(
    urls=urlpatterns
)
```
Прежде чем добвлять поиск вьюх подумаем о ситуациях когда роута может не быть и в ```snail/exceptions.py``` 
добавим ошибку 404 или NotFound
```python
class NotFound(Exception):
    code = 404
    text = 'Страница не найдена'
```
Теперь научим snail искать вьюху по роуту, пока немного примитивно, но потом мы это расширим. 
Сперва добавим непосредственно поиск роута
```python

import re
from typing import Type
from snail.exceptions import NotFound
from snail.view import View

class Snail:
    ...
    def _prepare_url(self, url: str):
        """Удаляем краевой /"""
        if url[-1] == '/':
            return url[:-1]
        return url

    def _find_view(self, raw_url: str) -> Type[View]:
        """Найти вьюху или отдать ошибку 404"""
        url = self._prepare_url(raw_url)
        for path in self.urls:
            m = re.match(path.url, url)
            if m is not None:
                return path.view
        raise NotFound
```
А потом обновим ```def __call__```, добавив туда вызов метода вьюхи соответствующего HTTP метода. 
Не забудем добавить ошибку когда происходит попытка обращения к несуществующему методу. Ошибку добавим в 
```snail/exceptions.py```
```python
class NotAllowed(Exception):
    code = 405
    text = 'Неподдерживаемый HTTP-метод'
```
```python
from snail.exceptions import NotAllowed


class Snail:
    ...
    def __call__(self, environ, start_response, **kwargs):
        raw_url = environ["PATH_INFO"]
        view = self._find_view(raw_url)()
        method = environ["REQUEST_METHOD"].lower()
        if not hasattr(view, method):
            raise NotAllowed
        raw_response = getattr(view, method)(None)
        response = raw_response.encode('utf-8')
        start_response("200 OK", [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(response)))
        ])
        return iter([response])
    
```
Перезапускаем сервер и все проверяем

Теперь додавим еще одну вьюху. 
Она будет делать особо сложную операцию, складывать числа которые мы передадим ей в get параметрах. 
Но тут мы сталкиваемся с проблемой, если мы все время будем передавть всю информацию в аргументы функции гет, то у нас банално распухнет функция. 
По этому мы введем объект Request. В ```snail/request.py```

```python
from urllib.parse import parse_qs

class Request:

    def __init__(self, environ: dict):
        self.build_get_params_dict(environ['QUERY_STRING'])

    def build_get_params_dict(self, raw_params: str):
        self.GET = parse_qs(raw_params)
```
Немного отрефакторим ```snail.main.Snail.__call__```

```python
from snail.exceptions import NotAllowed
from snail.view import View
from snail.request import Request

class Snail:
    ...
    def __call__(self, environ: dict, start_response, **kwargs):
        view = self._get_view(environ)
        request = self._get_request(environ)
        raw_response = self._get_response(environ, view, request)

        response = raw_response.encode('utf-8')
        start_response("200 OK", [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(response)))
        ])
        return iter([response])

    def _get_view(self, environ: dict) -> View:
        raw_url = environ["PATH_INFO"]
        view = self._find_view(raw_url)()
        return view

    def _get_request(self, environ: dict) -> Request:
        return Request(environ)

    def _get_response(self, environ: dict, view: View, request: Request) -> str:
        method = environ["REQUEST_METHOD"].lower()
        if not hasattr(view, method):
            raise NotAllowed
        return getattr(view, method)(request)
```
Теперь добавим нашу вьюху, и не забудем прописать урл для нее, урл без слеша в конце. Но сперва пропишем тайп хинты в 
```snail/view.py```
```python
from snail.request import Request

class View:

    def get(self, request: Request, *args, **kwargs):
        pass

    def post(self, request: Request, *args, **kwargs) :
        pass
```
```views.py```
```python
from snail.view import View

class EpicMath(View):

    def get(self, request, *args, **kwargs):
        first = request.GET.get('first')
        if not first or not first[0].isnumeric():
            return f'first пустое либо не является числом'

        second = request.GET.get('second')
        if not second or not second[0].isnumeric():
            return f'second пустое либо не является числом'

        return f'Сумма {first[0]} + {second[0]} = {int(first[0]) + int(second[0])}'
```
```urls.py```
```python
from snail.urls import Url
from views import Homepage, EpicMath


urlpatterns = [
    Url('^$', Homepage),
    Url('^/math$', EpicMath)
]
```
Если вы работаете на windows то у вас могла поехать кодировка
```
Ð¡ÑƒÐ¼Ð¼Ð° 1 + 2 = 3
```
Нужно явно указать кодировку документа в заголовках в ```snail.main.Snail.__call__```
```python
    def __call__(self, environ: dict, start_response, **kwargs):
        ...
        start_response("200 OK", [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(response)))
        ])
        return iter([response])
```
Теперь стало намного лучше.

Продолжим, у нас есть ошибка ```snail.exceptions.NotFound``` и хотелось бы отдавать HTTP код 404. 
Для того чтобы управлять заголовками и кодами ответа, введем класс Response
```snail/response.py```
```python
class Response:


    def __init__(self, status_code: int = 200, headers: dict = None, body: str = ''):
        self.status_code = status_code
        self.headers = {}
        self.body = b''
        self._set_base_headers()
        if headers is not None:
            self.update_headers(headers)
        self._set_body(body)


    def _set_base_headers(self):
        self.headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": 0
        }

    def _set_body(self, raw_body: str):
        self.body = raw_body.encode('utf-8')
        self.update_headers(
            {"Content-Length": str(len(self.body))}
        )
    
    def update_headers(self, headers: dict):
        self.headers.update(headers)

```
Снова обновим snail, потом перенесем все вьюхи и не забудем про тайпхинты
```snail.main.Snail```
```python
from snail.view import View
from snail.request import Request
from snail.response import Response

class Snail:
    ...

    def __call__(self, environ: dict, start_response, **kwargs):
        view = self._get_view(environ)
        request = self._get_request(environ)
        response = self._get_response(environ, view, request)
        start_response(str(response.status_code), response.headers.items())
        return iter([response.body])
    
    def _get_response(self, environ: dict, view: View, request: Request) -> Response:
        ...
```
```views.py```
```python
from snail.view import View
from snail.response import Response

class Homepage(View):

    def get(self, request, *args, **kwargs):
        return Response(body='hello world from view!')

class EpicMath(View):

    def get(self, request, *args, **kwargs):
        first = request.GET.get('first')
        if not first or not first[0].isnumeric():
            return Response(body=f'first пустое либо не является числом')

        second = request.GET.get('second')
        if not second or not second[0].isnumeric():
            return Response(body=f'second пустое либо не является числом')

        return Response(body=f'Сумма {first[0]} + {second[0]} = {int(first[0]) + int(second[0])}')
```
```snail/response.py```
```python
from snail.request import Request
from snail.response import Response

class View:

    def get(self, request: Request, *args, **kwargs) -> Response:
        pass

    def post(self, request: Request, *args, **kwargs) -> Response:
        pass
```
Перезапустим сервер и проверим. Работает!
Осталось 3 вещи которые нам нужно реализовать, это работа с POST запросом, Промежуточные слои (мидлвари) и шаблонизатор.
На счет последнего я не уверен, стоит ли его делать, ибо многие фреймворки живут и без него, но я исхожу что зритель 
новичек и шаблонизатор для него неотъемлимая часть фреймворка.
Добавим в класс Snail работу с настройками. А сами настройки будут передаваться в функции через класс Request.
```snail/request.py```
```python
class Request:

    def __init__(self, environ: dict, settings: dict):
        self.build_get_params_dict(environ['QUERY_STRING'])
        self.settings = settings
```
```snail/main.py```
```python
class Snail:

    __slots__ = ('urls', 'settings')

    def __init__(self, urls: List[Url], settings: dict):
        self.urls = urls
        self.settings = settings
    
    def _get_request(self, environ: dict) -> Request:
        return Request(environ, self.settings)
```
```main.py```
```python
import os   
from snail.main import Snail
from urls import urlpatterns

settings = {
    'BASE_DIR': os.path.dirname(os.path.abspath(__file__)),
    'TEMPLATES_DIR_NAME': 'templates'
}

app = Snail(
    urls=urlpatterns, settings=settings
)
```
Теперь создадим сам движек. Шаблонизатор будет только  вставлять переменные и цикл for, 
остальное можно реализовать похожим образом
Создадим файл ```snail/template_engine.py```
```python
import os
import re
from snail.request import Request

FOR_BLOCK_PATTERN = re.compile(r'{% for (?P<variable>[a-zA-Z]+) in (?P<seq>[a-zA-Z]+) %}(?P<content>[\S\s]+)(?={% endblock %}){% endblock %}')
VARIABLE_PATTERN = re.compile(r'{{ (?P<variable>[a-zA-Z_]+) }}')

class Engine:

    def __init__(self, base_dir, template_dir):
        self.template_dir = os.path.join(base_dir, template_dir)

    def _get_template_as_string(self, template_name) -> str:
        template_path = os.path.join(self.template_dir, template_name)
        if not os.path.isfile(template_path):
            raise Exception(f'template {template_path} not found')
        with open(template_path) as f:
            return f.read()

    def _build_block(self, context: dict, raw_template_block: str) -> str:
        used_vars = VARIABLE_PATTERN.findall(raw_template_block)
        if used_vars is None:
            return raw_template_block
        for var in used_vars:
            var_in_template = '{{ %s }}' % var
            raw_template_block = re.sub(var_in_template, str(context.get(var, '')), raw_template_block)
        return raw_template_block

    def _build_for_block(self, context: dict, raw_template: str):
        for_block = FOR_BLOCK_PATTERN.search(raw_template)
        if for_block is None:
            return raw_template
        built_for_block = ''
        for i in context.get(for_block.group('seq'), []):
            built_for_block += self._build_block(
                {**context, for_block.group('variable'): i},
                for_block.group('content')
            )
        raw_template = FOR_BLOCK_PATTERN.sub(built_for_block, raw_template)
        return raw_template

    def build(self, context: dict, template_name: str) -> str:
        raw_template = self._get_template_as_string(template_name)
        raw_template = self._build_for_block(context, raw_template)
        return self._build_block(context, raw_template)

def build_template(request:Request, context: dict, template_name: str) -> str:
    engine = Engine(
        request.settings.get('BASE_DIR'),
        request.settings.get('TEMPLATES_DIR_NAME')
    )
    return engine.build(context, template_name)
```
Обновление респонс чтобы у нас отрабатывало как html а не как текст
snail.response.Response
```python
class Response:
    ...
    def _set_base_headers(self):
        self.headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Content-Length": 0
        }
```
Сам шаблон. В корне проекта добавим папку templates в нее положим файл home.html с таким содержанием
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HomePage</title>
    <style>
        body {
            background-color: darkcyan;
        }
    </style>
</head>
<body>
Ура! Это Шаблон! Текущее время {{ time }}!
Посчитаем!
{% for i in lst %}
</br>
{{ i }}
{% endblock %}
</body>
</html>
```
Теперь пропишем во вьюху
views.Homepage
```python
from snail.view import View
from snail.response import Response
from snail.template_engine import build_template
from datetime import datetime

class Homepage(View):

    def get(self, request, *args, **kwargs):
        body = build_template(request, {'time': str(datetime.now()), 'lst': [1, 2, 3]}, 'home.html')
        return Response(body=body)
```
Проверяем, работает!
Теперь сделаем отдельную вьюху с формой, и сделаем post запрос
Добавляем в templates шаблон
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>
Привет {{ name }}!
<form action="">
  <p><b>Введите ваше имя:</b></p>
  <p><input type="text" name="answer" /><Br>
  <p><input type="submit"></p>
 </form>
</body>
</html>
```
обновим request
```python
from urllib.parse import parse_qs

class Request:

    def __init__(self, environ: dict, settings: dict):
        self.build_get_params_dict(environ['QUERY_STRING'])
        self.build_post_params_dict(environ['wsgi.input'].read())
        self.settings = settings

    def build_get_params_dict(self, raw_params: str):
        self.GET = parse_qs(raw_params)

    def build_post_params_dict(self, raw_bytes: bytes):
        raw_params = raw_bytes.decode('utf-8')
        self.POST = parse_qs(raw_params)
```
Во view добавим еще одну вьюху
```python
class Hello(View):

    def get(self, request, *args, **kwargs):
        body = build_template(request, {'name': 'незнакомец'}, 'hello.html')
        return Response(body=body)

    def post(self, request, *args, **kwargs):
        raw_name = request.POST.get('name')
        name = raw_name[0] if raw_name else 'незнакомец'
        body = build_template(request, {'name': name}, 'hello.html')
        return Response(body=body)
```

И остались мидлвари, напишем работу с ними и простой мидлварь сессии
Добавим в snail/middleware следующий код
```python
from snail.request import Request
from snail.response import Response

class BaseMiddleware:

    def to_request(self, request: Request):
        return 

    def to_response(self, response: Response):
        return 
```
Добавим в Request и Response возможность использовать кастомные поля
```python
class Request:

    def __init__(self, environ: dict, settings: dict):
        ...
        self.environ = environ
        self.extra = {}

    def __getattr__(self, item):
        return self.extra.get(item, None)
```
```python
class Response:
    def __init__(self, request, status_code: int = 200, headers: dict = None, body: str = ''):
        ...
        self.request = request
        self.extra = {}
    
    def __getattr__(self, item):
        return self.extra.get(item)
```
Не забудем обновить вьюхи

Добавим в качестве примера одну мидлварь которая будет встроена в фреймворк, она будет добавлять куки пользователю
```python
from snail.request import Request
from snail.response import Response
from uuid import uuid4
from urllib.parse import parse_qs

class BaseMiddleware:

    def to_request(self, request: Request):
        return

    def to_response(self, response: Response):
        return


class Session:

    def to_request(self, request: Request):
        cookie = request.environ.get('HTTP_COOKIE', None)
        if not cookie:
            return
        session_id = parse_qs(cookie)['session_id'][0]
        request.extra['session_id'] = session_id

    def to_response(self, response: Response):
        if not response.request.session_id:
            response.update_headers(
                {"Set-Cookie": f"session_id={uuid4()}"}
            )

middlewares = [
    Session
]
```
Обновим класс Snail чтобы они принимал middleware и работал с ними
```python
from snail.urls import Url
from typing import List
from snail.request import Request
from snail.response import Response
from snail.middleware import BaseMiddleware

class Snail:

    __slots__ = ('urls', 'settings', 'middlewares')

    def __init__(self, urls: List[Url], settings: dict, middlewares: List[Type[BaseMiddleware]]):
        self.urls = urls
        self.settings = settings
        self.middlewares = middlewares


    def __call__(self, environ: dict, start_response, **kwargs):
        view = self._get_view(environ)
        request = self._get_request(environ)
        self._apply_middleware_to_request(request)
        response = self._get_response(environ, view, request)
        self._apply_middleware_to_response(response)
        start_response(str(response.status_code), response.headers.items())
        return iter([response.body])

    def _apply_middleware_to_request(self, request: Request):
        for i in self.middlewares:
            i().to_request(request)
    
    def _apply_middleware_to_response(self, response: Response):
        for i in self.middlewares:
            i().to_response(response) 
```
```python
import os
from snail.main import Snail
from urls import urlpatterns
from snail.middleware import middlewares

settings = {
    'BASE_DIR': os.path.dirname(os.path.abspath(__file__)),
    'TEMPLATES_DIR_NAME': 'templates'
}

app = Snail(
    urls=urlpatterns, settings=settings, middlewares=middlewares
)
```