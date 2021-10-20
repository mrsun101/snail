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