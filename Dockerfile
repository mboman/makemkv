FROM fedora:25
MAINTAINER Michael Boman <michael@michaelboman.org>

RUN dnf update -qy && \
    dnf install -qy dnf-plugins-core sudo && \
    dnf config-manager --add-repo=https://negativo17.org/repos/fedora-multimedia.repo && \
    dnf install -qy makemkv && \
    dnf clean all && \
    sudo useradd -s /sbin/nologin -G cdrom mkv && \
    sudo -u mkv mkdir /home/mkv/.MakeMKV

VOLUME /output
WORKDIR /output
COPY bin/env.sh /
COPY bin/rip.sh /
COPY etc/settings.conf /home/mkv/.MakeMKV/
COPY lib/wrappers.so /

CMD ["/rip.sh"]
