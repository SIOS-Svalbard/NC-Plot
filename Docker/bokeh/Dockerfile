FROM epinux/sci-fastapi

RUN pip install --upgrade pip setuptools \
    ipywidgets_bokeh \
    ipyleaflet \
    python-geohash \
    geopandas \
    openlocationcode \
    osm2geojson \ 
    geohash \
    osm2geojson \
    openlocationcode \
    datashader \
    holoviews \
    geoviews \
    datashader \
    panel \
    && echo "### Cleanup unneeded files" && \
    rm -rf /usr/lib/python3*/*/tests && \
    rm -rf /usr/lib/python3*/ensurepip && \
    rm -rf /usr/lib/python3*/idlelib && \
    rm -f /usr/lib/python3*/distutils/command/*exe && \
    rm -rf /usr/share/man/* && \
    clean-pyc-files /usr/lib/python3*

RUN apt-get update && apt-get install -y software-properties-common curl && curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get update && apt-get install nodejs
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 5100
ENV ORIGIN="epinux.com:5100" PORT="5100" PREFIX="" LOG_LEVEL="info"

COPY ./app /app
ENTRYPOINT ["./entrypoint.sh"]