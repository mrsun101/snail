from snail.view import View
from snail.response import Response
from snail.template_engine import build_template
from datetime import datetime

class Homepage(View):

    def get(self, request, *args, **kwargs):
        body = build_template(request, {'time': str(datetime.now()), 'lst': [1, 2, 3]}, 'home.html')
        return Response(request, body=body)

class EpicMath(View):

    def get(self, request, *args, **kwargs):
        first = request.GET.get('first')
        if not first or not first[0].isnumeric():
            return Response(request, body=f'first пустое либо не является числом')

        second = request.GET.get('second')
        if not second or not second[0].isnumeric():
            return Response(request, body=f'second пустое либо не является числом')

        return Response(request, body=f'Сумма {first[0]} + {second[0]} = {int(first[0]) + int(second[0])}')


class Hello(View):

    def get(self, request, *args, **kwargs):
        body = build_template(request, {'name': 'незнакомец'}, 'hello.html')
        return Response(request, body=body)

    def post(self, request, *args, **kwargs):
        raw_name = request.POST.get('name')
        name = raw_name[0] if raw_name else 'незнакомец'
        body = build_template(request, {'name': name}, 'hello.html')
        return Response(request, body=body)
