FROM python:3.10

RUN apt-get update && apt-get install -y autoconf libtool npm wget
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:ubuntugis/ppa
RUN apt-get install -y gdal-bin libgdal-dev libsqlite3-mod-spatialite
RUN ln -s /usr/bin/nodejs /usr/local/bin/node
RUN wget -O /tmp/dart-sass.tar.gz https://github.com/sass/dart-sass/releases/download/1.56.1/dart-sass-1.56.1-linux-x64.tar.gz && \
    tar -xzf /tmp/dart-sass.tar.gz -C /usr/local/bin && \
    rm -rf /tmp/dart-sass.tar.gz && \
    mv /usr/local/bin/dart-sass/sass /usr/local/bin/sass && \
    rm -rf /usr/local/bin/dart-sass

ENTRYPOINT ["tail", "-f", "/dev/null"]