class NotFound(Exception):
    code = 404
    text = 'Страница не найдена'

class NotAllowed(Exception):
    code = 405
    text = 'Неподдерживаемый HTTP-метод'