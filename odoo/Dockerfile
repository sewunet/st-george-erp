ARG ODOO_VERSION
FROM ghcr.io/tecnativa/doodba:${ODOO_VERSION}-onbuild

# Change Directory Owner & Install wkhtmltopdf
USER root
RUN chown -R odoo:odoo /opt/odoo \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

USER odoo
