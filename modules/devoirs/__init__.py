# modules/devoirs/__init__.py

def setup_devoirs_commands(bot):
    from .add import setup_add
    from .delete import setup_delete
    from .list import setup_list

    setup_add(bot)
    setup_delete(bot)
    setup_list(bot)
