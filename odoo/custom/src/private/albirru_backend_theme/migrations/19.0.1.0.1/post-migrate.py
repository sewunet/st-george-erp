# -*- coding: utf-8 -*-
"""Repair bookmark names that were HTML-escaped at storage time.

Earlier versions escaped the bookmark name in the controller before writing it
to the database. Templates escape again at render time, so names containing
characters such as ``&`` or ``<`` were displayed as entities ("Sales &amp; Ops").
Escaping now happens only at output, so the stored values must be unescaped.
"""
import html
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT id, name
          FROM albirru_bookmark
         WHERE name LIKE '%%&%%;%%'
    """)
    rows = cr.fetchall()

    repaired = 0
    for bookmark_id, name in rows:
        # Unescape repeatedly: a name could have been escaped more than once if
        # it was edited through the old endpoint several times.
        clean = name
        for _ in range(5):
            unescaped = html.unescape(clean)
            if unescaped == clean:
                break
            clean = unescaped

        if clean != name:
            cr.execute(
                "UPDATE albirru_bookmark SET name = %s WHERE id = %s",
                (clean, bookmark_id),
            )
            repaired += 1

    if repaired:
        _logger.info('Albirru: unescaped %s bookmark name(s).', repaired)
