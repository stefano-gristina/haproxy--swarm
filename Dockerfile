# vim:set ft=dockerfile:
FROM alpine:3.7

ENV HAPROXY_MAJOR 1.8
ENV HAPROXY_VERSION 1.8.8
ENV HAPROXY_MD5 8633b6e661169d2fc6a44d82a3aceae5

# see https://sources.debian.net/src/haproxy/jessie/debian/rules/ for some helpful navigation of the possible "make"arguments
RUN set -x \
        \
        && apk add --no-cache --virtual .build-deps \
                ca-certificates \
                gcc \
                libc-dev \
                linux-headers \
                lua5.3-dev \
                make \
                openssl \
                openssl-dev \
                pcre-dev \
                readline-dev \
                tar \
                zlib-dev \
        \
# install HAProxy
        && wget -O haproxy.tar.gz "https://www.haproxy.org/download/${HAPROXY_MAJOR}/src/haproxy-${HAPROXY_VERSION}.tar.gz" \
        && echo "$HAPROXY_MD5 *haproxy.tar.gz" | md5sum -c \
        && mkdir -p /usr/src/haproxy \
        && tar -xzf haproxy.tar.gz -C /usr/src/haproxy --strip-components=1 \
        && rm haproxy.tar.gz \
        \
        && makeOpts=' \
                TARGET=linux2628 \
                USE_LUA=1 LUA_INC=/usr/include/lua5.3 LUA_LIB=/usr/lib/lua5.3 \
                USE_OPENSSL=1 \
                USE_PCRE=1 PCREDIR= \
                USE_ZLIB=1 \
        ' \
        && make -C /usr/src/haproxy -j "$(getconf _NPROCESSORS_ONLN)" all $makeOpts \
        && make -C /usr/src/haproxy install-bin $makeOpts \
        \
        && mkdir -p /usr/local/etc/haproxy \
        && cp -R /usr/src/haproxy/examples/errorfiles /usr/local/etc/haproxy/errors \
        && rm -rf /usr/src/haproxy \
        \
        && runDeps="$( \
                scanelf --needed --nobanner --format '%n#p' --recursive /usr/local \
                        | tr ',' '\n' \
                        | sort -u \
                        | awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 { next } { print "so:" $1 }' \
        )" \
        && apk add --virtual .haproxy-rundeps $runDeps \
        && apk del .build-deps \

# install python
        && apk update \
        && apk add python \
        && apk add py2-pip \
        && apk add bind-tools \

#Install python library
       && pip install requests \
       && pip install Template \
       && pip install logger \
       && mkdir /var/run/hapee-1.7

COPY docker-entrypoint.sh /
COPY check-service.py /bin
COPY haproxy.cfg /usr/local/etc/haproxy
COPY haproxy.tmpl /usr/local/etc/haproxy
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
