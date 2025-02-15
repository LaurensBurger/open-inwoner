from django import template

from open_inwoner.components.utils import ContentsNode, parse_component_with_args

from ...pdc.models import Category

register = template.Library()


@register.inclusion_tag("components/Card/Card.html")
def card(href, title, **kwargs):
    """
    Render in a card. Only using variables.

    Usage:
        {% card href="https://maykinmedia.nl" %}

    Variables:
        + href: url | where the card links to.
        + title: string | this will be the card title.
        - alt: string | the alt of the header image.
        - compact: bool | Whether to use compact styling.
        - direction: string | can be set to "horizontal" to show contents horizontally.
        - inline: bool | Whether the card should be rendered inline.
        - src: string | the src of the header image.
        - stretch: bool | Whether to stretch the card vertically.
        - tinted: bool | whether to use gray as background color.
        - type: string (info) | Set to info for an info card.
        - image: FilerImageField | an image that should be used.
        - image_object_fit: string | Can be set to either "cover" (default) or "contain".
        - grid: boolean | if the card should be a grid.
    """
    return {**kwargs, "href": href, "title": title}


@register.tag
def render_card(parser, token):
    """
    Render in a card. Using nested elements.

    Usage:
        {% render_card %}
            <h1 class="h1">{% trans 'Welkom' %}</h1>
        {% endrender_card %}

    Variables:
        - grid: boolean | if the card should be a grid.

    Extra context:
        - contents: string (HTML) | this is the context between the render_card and endrender_card tags
    """
    bits = token.split_contents()
    context_kwargs = parse_component_with_args(parser, bits, "render_card")
    nodelist = parser.parse(("endrender_card",))
    parser.delete_first_token()
    return ContentsNode(nodelist, "components/Card/RenderCard.html", **context_kwargs)


@register.inclusion_tag("components/Card/CategoryCard.html")
def category_card(category: Category, **kwargs):
    """
    Renders a card prepopulated based on `category`.

    Usage:
        {% category_card category %}

    Available options:
        - category: Category | the category to render card for.
    """
    return {**kwargs, "category": category}


@register.inclusion_tag("components/Card/DescriptionCard.html")
def description_card(title, description, url, **kwargs):
    """
    Renders a card prepopulated based on `product`.

    Usage:
        {% description_card title=product.title description=product.intro url=product.get_absolute_url %}
        {% description_card title="title" description="description" url="https://maykinmedia.nl" %}

    Available options:
        + title: string | The title of the card that needs to be displayed.
        + description: string | The description that needs to be displayed.
        + url: string | The url that the card should point to.
        - object: any | The object that needs to render aditional data.
        - image: FilerImageField | an image that should be used.
    """
    kwargs.update(title=title, description=description, url=url)
    return kwargs


@register.inclusion_tag("components/Card/ProductCard.html")
def product_card(description, url, **kwargs):
    """
    Renders a card with or without an image prepopulated based on `product`.

    Usage:
        {% product_card title=product.title description=product.intro url=product.get_absolute_url %}

    Available options:
        + description: string | The description that needs to be displayed.
        + url: string | The url that the card should point to.
        - title: string | The title of the card that may be displayed if there is no image.
        - object: any | The object that needs to render aditional data.
        - image: FilerImageField | an image that should be used.
    """
    kwargs.update(description=description, url=url)
    return kwargs


@register.inclusion_tag("components/Card/CardContainer.html")
def card_container(categories=[], subcategories=[], products=[], plans=[], **kwargs):
    """
    A card container where the category card or product card will be rendered in.

    Usage:
        {% card_container categories=categories %}

    Variables:
        - categories: Category[] | categories to render.
        - subcategories: Category[] | subcategories to render.
        - products: Product[] | products to render.
        - parent: Category | The parent of the given card_container
        - image_object_fit: string | Can be set to either "cover" (default) or "contain".
    """
    if (
        categories is None
        and subcategories is None
        and products is None
        and plans is None
    ):
        assert False, "provide categories, subcategories, products or plans"

    return {
        **kwargs,
        "categories": categories,
        "subcategories": subcategories,
        "products": products,
        "plans": plans,
    }


@register.tag()
def render_card_container(parser, token):
    """
    Nested content supported.

    Usage:
        {% render_card_container %}
            {% card href='https://www.example.com' title='example.com' %}
        {% endrender_card_container %}

    Variables:
        Supports all options from card, but optional.

     Extra context:
         - contents: string (HTML) | this is the context between the render_card and endrender_card tags
    """
    bits = token.split_contents()
    context_kwargs = parse_component_with_args(parser, bits, "render_list")
    nodelist = parser.parse(("endrender_card_container",))  # End tag
    parser.delete_first_token()
    return ContentsNode(
        nodelist, "components/Card/CardContainer.html", **context_kwargs
    )  # Template
