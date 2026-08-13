# Scrapling web provider plugin.

from plugins.web.scrapling.provider import ScraplingWebProvider

def register(ctx):
    ctx.register_web_search_provider(ScraplingWebProvider())
