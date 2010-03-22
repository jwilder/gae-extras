# Copyright 2010 Jason Wilder (jasonwilder.com). All Rights Reserved.

from django import template
from django.template import Node, resolve_variable
from django.template import TemplateSyntaxError, loader

register = template.Library()

class FragmentNode(Node):
    """
    Includes a template fragment into the current template.  The fragment
    can accept parameters in a new scoped context.

    For example, to include a ''fragments.html'', use::

        {% fragment "fragments.html" %}
        {% endfragment %}

    where ''fragments.html'' is only the HTML markup you wish to include.  For
    example,

        <div>
          <label>{{ labelName }}</label>
          <input type="text" name="{{ fieldName }}" value="{{ fieldValue }}"/>
        </div>

    In addition, fragments can have parameters by including
    ''{% param name value %}'' tag within the body of the ''{% fragment %}''
    tag.  Parameters can be strings or variables in addition to having filter
    expression.  The parameters are scoped to the ''{% fragment %}'' block and
    are not accessible after the block ends::


        {% fragment "fragments.html" %}
          {% param labelName "Username" %}
          {% param fieldName "Username"|lower %}
          {% param fieldValue request.user.username %}
        {% endfragment %}


    Parameters can also have bodies that can be arbitrary markup such as:

        {% fragment "fragments.html" %}
          {% param labelName %}
            <b>{{ request.user.username }}</b>
          {% endparam %}
        {% endfragment %}

    Parameters can also nest other fragments to create very a flexible
    template system in addition to Django's template inheritance approach:

        {% fragment "fragments.html" %}
          {% param formField %}
            {% fragment "field.html" %}
              {% param name request.user.username %}
            {% endfragment %}
          {% endparam %}
        {% endfragment %}

    This is useful for extending fragments fragments in special cases.

    """
    def __init__(self, template_name, params):
        self.template_name = template_name
        self.params = params

    def render(self, context):
        template = loader.get_template(resolve_variable(self.template_name, context))

        context.push()
        context[FragmentNode.__class__.__name__] = True
        for i in self.params:
            i.render(context)
        body = template.render(context)
        del context[FragmentNode.__class__.__name__]
        context.pop()

        return body

@register.tag
def fragment(parser, token):
    tag, template_name = token.split_contents()
    params = parser.parse(('end'+tag))
    parser.delete_first_token()
    return FragmentNode(template_name, params)

class ParamNode(Node):
    def __init__(self, name, value=None, body_value=None):
        self.name = name
        self.value = value
        self.body_value = body_value

    def render(self, context):
        if  FragmentNode.__class__.__name__ not in context:
            raise TemplateSyntaxError("param tag must be nested within fragment")
        if self.value:
            context[self.name] = self.value.resolve(context)
        elif self.body_value:
            context[self.name] = self.body_value.render(context)
        return ""
@register.tag
def param(parser, token):
    bits = token.contents.split()

    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' statements needs a variable name"
                                  ": %s" % (bits[0], token.contents))
    value = None
    if len(bits) > 2:
        value = parser.compile_filter(" ".join(bits[2:]))

    body_value = None
    if not value:
        body_value = parser.parse(('end'+bits[0]))
        parser.delete_first_token()

    return ParamNode(bits[1], value, body_value)


