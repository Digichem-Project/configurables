import importlib


from configurables.util import getopt
from docutils import nodes

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective


class ConfigurablesDirective(SphinxDirective):
    """"""

    required_arguments = 2

    @classmethod
    def build_nodes(self, definition, _path = None):
        _path = _path if _path is not None else []
        _path.append(definition['name'])


        def_node = nodes.definition_list_item()
        def_node += nodes.term(definition['name'], definition['name'])

        if "type" in definition and definition['type'] is not None:
            def_node += nodes.classifier(definition['type'], definition['type'])
        
        # if "required" in definition and definition['required']:
        #     def_node += nodes.classifier("required", "required")

        if "choices" in definition and len(definition["choices"]):
            choices_txt = "({})".format(", ".join((str(item) for item in definition['choices'])))
            def_node += nodes.classifier(choices_txt, choices_txt)
            #definition_body += nodes.paragraph(text="Choices: {}".format(", ".join((str(item) for item in definition['choices']))))
        
        if "default" in definition and definition['default'] is not None:
            def_node += nodes.classifier("[{}]".format(definition['default']), "[{}]".format(definition['default']))

        definition_body = nodes.definition()
        if "help" in definition:
            definition_body += nodes.paragraph(text=definition['help'])
        def_node += definition_body

        if "children" in definition:
            child_defs = nodes.definition_list()
            for child in definition['children'].values():
                child_defs += self.build_nodes(child, _path)

            definition_body += child_defs

        return def_node


    def run(self):
        # First, import the correct module.
        module = importlib.import_module(self.arguments[0])

        # Split our path.
        path = self.arguments[1].split(":")
        # Get top-level object.
        base = getattr(module, path[0])

        # Get the specific option.
        if len(path) > 1:
            option = getopt(base, *path[1:])
            definition = option.describe(base)
        
        else:
            option = base
            definition = option.describe()

        def_list = nodes.definition_list()
        def_list += self.build_nodes(definition)

        return [def_list]


def setup(app: Sphinx):
    app.add_directive('configurable', ConfigurablesDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }