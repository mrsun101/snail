import re
from snail.urls import Url
from typing import List, Type
from snail.exceptions import NotFound, NotAllowed
from snail.view import View
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
        from pprint import pprint; pprint(environ)
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

    def _get_view(self, environ: dict) -> View:
        raw_url = environ["PATH_INFO"]
        view = self._find_view(raw_url)()
        return view

    def _get_request(self, environ: dict) -> Request:
        return Request(environ, self.settings)

    def _get_response(self, environ: dict, view: View, request: Request) -> Response:
        method = environ["REQUEST_METHOD"].lower()
        if not hasattr(view, method):
            raise NotAllowed
        return getattr(view, method)(request)

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



