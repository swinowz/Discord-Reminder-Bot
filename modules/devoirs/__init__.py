# modules/devoirs/__init__.py

from .delete import setup_delete
from .list import setup_list
from .add import setup_add_commands

def setup_devoirs_commands(bot):
    setup_add_commands(bot)
    setup_delete(bot)
    setup_list(bot)
