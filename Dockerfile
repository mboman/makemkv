FROM alpine:latest
MAINTAINER Michael Boman <michael@michaelboman.org>

RUN apk --update-cache upgrade && \
    apk add sudo && \
    sudo adduser --disabled-password -s /sbin/nologin -G cdrom mkv && \
    sudo -u mkv mkdir /home/mkv/.MakeMKV

ADD makemkv-builder/makemkv.tar.gz /

VOLUME /output
WORKDIR /output
COPY bin/env.sh /
COPY bin/rip.sh /
COPY etc/settings.conf /home/mkv/.MakeMKV/
COPY lib/wrappers.so /

CMD ["/rip.sh"]
