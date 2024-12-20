"""Catch-all for tests that use template tags and don't fit other files"""

from typing import Callable

from django.template import Context, Template

from django_components import Component, register, registry, types

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase, parametrize_context_behavior

setup_test_config({"autodiscover": False})


class SlottedComponent(Component):
    template_name = "slotted_template.html"


#######################
# TESTS
#######################


class TemplateInstrumentationTest(BaseTestCase):
    saved_render_method: Callable  # Assigned during setup.

    def tearDown(self):
        super().tearDown()
        Template._render = self.saved_render_method

    def setUp(self):
        """Emulate Django test instrumentation for TestCase (see setup_test_environment)"""
        super().setUp()

        from django.test.utils import instrumented_test_render

        self.saved_render_method = Template._render
        Template._render = instrumented_test_render

        registry.clear()
        registry.register("test_component", SlottedComponent)

        @register("inner_component")
        class SimpleComponent(Component):
            template_name = "simple_template.html"

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

            class Media:
                css = "style.css"
                js = "script.js"

    def templates_used_to_render(self, subject_template, render_context=None):
        """Emulate django.test.client.Client (see request method)."""
        from django.test.signals import template_rendered

        templates_used = []

        def receive_template_signal(sender, template, context, **_kwargs):
            templates_used.append(template.name)

        template_rendered.connect(receive_template_signal, dispatch_uid="test_method")
        subject_template.render(render_context or Context({}))
        template_rendered.disconnect(dispatch_uid="test_method")
        return templates_used

    @parametrize_context_behavior(["django", "isolated"])
    def test_template_shown_as_used(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}{% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_component_templates_all_shown_as_used(self):
        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test_component' %}
              {% fill "header" %}
                {% component 'inner_component' variable='foo' %}{% endcomponent %}
              {% endfill %}
            {% endcomponent %}
        """
        template = Template(template_str, name="root")
        templates_used = self.templates_used_to_render(template)
        self.assertIn("slotted_template.html", templates_used)
        self.assertIn("simple_template.html", templates_used)


class BlockCompatTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_extends(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_extends")
        class SlotInsideExtendsComponent(Component):
            template: types.django_html = """
                {% extends "block_in_slot_in_component.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_extends" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>BODY_FROM_FILL</main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slots_inside_include(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_include")
        class SlotInsideIncludeComponent(Component):
            template: types.django_html = """
                {% include "block_in_slot_in_component.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_include" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>BODY_FROM_FILL</main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_component_inside_block(self):
        registry.register("slotted_component", SlottedComponent)
        template: types.django_html = """
            {% extends "block.html" %}
            {% load component_tags %}
            {% block body %}
            {% component "slotted_component" %}
                {% fill "header" %}{% endfill %}
                {% fill "main" %}
                TEST
                {% endfill %}
                {% fill "footer" %}{% endfill %}
            {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
            <main role="main">
            <div class='container main-container'>
                <custom-template>
                <header></header>
                <main>TEST</main>
                <footer></footer>
                </custom-template>
            </div>
            </main>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_inside_component(self):
        registry.register("slotted_component", SlottedComponent)

        template: types.django_html = """
            {% extends "block_in_component.html" %}
            {% load component_tags %}
            {% block body %}
            <div>
                58 giraffes and 2 pantaloons
            </div>
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    <div> 58 giraffes and 2 pantaloons </div>
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_inside_component_parent(self):
        registry.register("slotted_component", SlottedComponent)

        @register("block_in_component_parent")
        class BlockInCompParent(Component):
            template_name = "block_in_component_parent.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_in_component_parent" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    <div> 58 giraffes and 2 pantaloons </div>
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_block_does_not_affect_inside_component(self):
        """
        Assert that when we call a component with `{% component %}`, that
        the `{% block %}` will NOT affect the inner component.
        """
        registry.register("slotted_component", SlottedComponent)

        @register("block_inside_slot_v1")
        class BlockInSlotInComponent(Component):
            template_name = "block_in_slot_in_component.html"

        template: types.django_html = """
            {% load component_tags %}
            {% component "block_inside_slot_v1" %}
                {% fill "body" %}
                    BODY_FROM_FILL
                {% endfill %}
            {% endcomponent %}
            {% block inner %}
                wow
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>BODY_FROM_FILL</main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
            wow
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_default_block_default(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    Default inner
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_default_block_override(self):
        registry.clear()
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
                {% block inner %}
                    INNER BLOCK OVERRIDEN
                {% endblock %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    INNER BLOCK OVERRIDEN
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["isolated", "django"])
    def test_slot_inside_block__slot_overriden_block_default(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
            """

        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}
                {% fill "body" %}
                    SLOT OVERRIDEN
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    SLOT OVERRIDEN
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_slot_inside_block__slot_overriden_block_overriden(self):
        registry.register("slotted_component", SlottedComponent)

        @register("slot_inside_block")
        class _SlotInsideBlockComponent(Component):
            template: types.django_html = """
                {% extends "slot_inside_block.html" %}
                {% block inner %}
                    {% load component_tags %}
                    {% slot "new_slot" %}{% endslot %}
                {% endblock %}
                whut
            """

        # NOTE: The "body" fill will NOT show up, because we override the `inner` block
        # with a different slot. But the "new_slot" WILL show up.
        template: types.django_html = """
            {% load component_tags %}
            {% component "slot_inside_block" %}
                {% fill "body" %}
                    SLOT_BODY__OVERRIDEN
                {% endfill %}
                {% fill "new_slot" %}
                    SLOT_NEW__OVERRIDEN
                {% endfill %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    Helloodiddoo
                    SLOT_NEW__OVERRIDEN
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_inject_inside_block(self):
        registry.register("slotted_component", SlottedComponent)

        @register("injectee")
        class InjectComponent(Component):
            template: types.django_html = """
                <div> injected: {{ var|safe }} </div>
            """

            def get_context_data(self):
                var = self.inject("block_provide")
                return {"var": var}

        template: types.django_html = """
            {% extends "block_in_component_provide.html" %}
            {% load component_tags %}
            {% block body %}
                {% component "injectee" %}
                {% endcomponent %}
            {% endblock %}
        """
        rendered = Template(template).render(Context())
        expected = """
            <!DOCTYPE html>
            <html lang="en">
            <body>
                <custom-template>
                <header></header>
                <main>
                    <div> injected: DepInject(hello='from_block') </div>
                </main>
                <footer>Default footer</footer>
                </custom-template>
            </body>
            </html>
        """
        self.assertHTMLEqual(rendered, expected)


class MultilineTagsTests(BaseTestCase):
    @parametrize_context_behavior(["django", "isolated"])
    def test_multiline_tags(self):
        @register("test_component")
        class SimpleComponent(Component):
            template: types.django_html = """
                Variable: <strong>{{ variable }}</strong>
            """

            def get_context_data(self, variable, variable2="default"):
                return {
                    "variable": variable,
                    "variable2": variable2,
                }

        template: types.django_html = """
            {% load component_tags %}
            {% component
                "test_component"
                123
                variable2="abc"
            %}
            {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong>123</strong>
        """
        self.assertHTMLEqual(rendered, expected)


class NestedTagsTests(BaseTestCase):
    class SimpleComponent(Component):
        template: types.django_html = """
            Variable: <strong>{{ var }}</strong>
        """

        def get_context_data(self, var):
            return {
                "var": var,
            }

    # See https://github.com/EmilStenstrom/django-components/discussions/671
    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_tags(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var="{% lorem 1 w %}" %}{% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong>lorem</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_single(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_("organisation's") %} {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong>organisation's</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_single_self_closing(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_("organisation's") / %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong>organisation's</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_double(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_('organisation"s') %} {% endcomponent %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong>organisation"s</strong>
        """
        self.assertHTMLEqual(rendered, expected)

    @parametrize_context_behavior(["django", "isolated"])
    def test_nested_quote_double_self_closing(self):
        registry.register("test", self.SimpleComponent)

        template: types.django_html = """
            {% load component_tags %}
            {% component "test" var=_('organisation"s') / %}
        """
        rendered = Template(template).render(Context())
        expected = """
            Variable: <strong>organisation"s</strong>
        """
        self.assertHTMLEqual(rendered, expected)
