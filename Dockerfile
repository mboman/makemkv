FROM ubuntu:bionic as builder
MAINTAINER Michael Boman <michael@michaelboman.org>
COPY makemkv-builder/builder /builder
RUN /builder/build.sh /output

FROM alpine:latest
MAINTAINER Michael Boman <michael@michaelboman.org>

RUN apk --update-cache upgrade && \
    apk add sudo && \
    sudo adduser --disabled-password -s /sbin/nologin -G cdrom mkv && \
    sudo -u mkv mkdir /home/mkv/.MakeMKV

#COPY --from=builder /output/makemkv.tar.gz /makemkv.tar.gz
#RUN tar -x -p -C / /makemkv.tar.gz && rm -f /makemkv.tar.gz
COPY --from=builder /tmp/makemkv-install/opt /opt

VOLUME /output
WORKDIR /output
COPY bin/env.sh /
COPY bin/rip.sh /
COPY etc/settings.conf /home/mkv/.MakeMKV/
COPY lib/wrappers.so /

CMD ["/rip.sh"]
