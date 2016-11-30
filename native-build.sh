#!/bin/bash
#
# Script to build QT5 natively on the sysroot.
#
# This allows to build QT5 apps on the RaspberryPI
#

qt5_install=$1

qt5_builddeps="libc6-dev libxcb1-dev libxcb-icccm4-dev libxcb-xfixes0-dev \
libxcb-image0-dev libxcb-keysyms1-dev libxcomposite-dev \
libxcb-sync0-dev libxcb-randr0-dev libx11-xcb-dev libxcb-render-util0-dev \
libxrender-dev libxext-dev libxcb-glx0-dev pkg-config \
libssl-dev libraspberrypi-dev libfreetype6-dev libxi-dev libcap-dev \
libwayland-dev libxkbcommon-dev build-essential git-core libfontconfig1-dev \
libasound2-dev libinput-dev libmtdev-dev libproxy-dev libdirectfb-dev \
libts-dev libudev-dev libxcb-xinerama0-dev \
libdbus-1-dev libicu-dev libglib2.0-dev time"

if [ "$qt5_install" == "" ]; then
    echo "Syntax error: native-build.sh <qt5 install directory>"
    exit 1
fi

if [ `uname -m` != "armv7l" ]; then
    echo "Not running in emulated ARM mode - aborting"
    exit 1
fi

apt-get update
apt-get install -y --no-install-recommends $qt5_builddeps

echo ">>> Configure..."
configure_options="
-opengl es2 -eglfs -xcb -device linux-rasp-pi2-g++
-device-option CROSS_COMPILE=/usr/bin/
-sysroot / -opensource -confirm-license -release -skip qtwayland
-prefix /usr/local/qt5 -no-pch -alsa -no-use-gold-linker -qt-xkbcommon
-xkb-config-root /usr/share/X11/xkb -skip qtwebengine -skip qtwebview
-nomake tests -nomake examples -verbose -no-warnings-are-errors
-no-qml-debug -optimized-qmake -strip -fontconfig
"
cd /tmp/qt5
/usr/bin/time ./configure $configure_options

exit 0

echo ">> Make..."
make -j 9

echo ">> Make Install..."
make install
