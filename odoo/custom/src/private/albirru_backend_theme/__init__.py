# -*- coding: utf-8 -*-
import logging

from . import models
from . import controllers

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    """Undo the global side effects this module applies on install.

    data/theme_data.xml deactivates base.menu_tests. That menu belongs to the
    base module, so leaving it hidden after an uninstall would silently affect
    an installation that no longer has this theme.
    """
    menu = env.ref('base.menu_tests', raise_if_not_found=False)
    if menu and not menu.active:
        menu.active = True
        _logger.info('Albirru: restored base.menu_tests on uninstall.')
