from slug import slugify


def article_slug(title: str) -> str:
    return slugify(title)
