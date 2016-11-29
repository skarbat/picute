#!/bin/bash
#
# Script to build QT5 natively on the sysroot.
#
# This allows to build QT5 apps on the RaspberryPI
#

qt5_install=$1

if [ "$qt5_install" == "" ]; then
    echo "Syntax error: native-build.sh <qt5 install directory>"
    exit 1
fi

if [ `uname -m` != "armv7l" ]; then
    echo "Not running in emulated ARM mode - aborting"
    exit 1
fi

echo ">>> Configure..."
cd /tmp/qt5
./configure -device linux-rasp-pi2-g++ \
	    -device-option CROSS_COMPILE=/usr/bin/ \
	    -opensource -confirm-license -release \
	    -prefix $qt5_install -pkg-config -no-pch \
	    -skip qtwebengine -skip qtwebview -skip qtwayland \
	    -no-use-gold-linker -xkb-config-root /usr/share/X11/xkb \
	    -nomake tests -nomake examples -verbose -no-warnings-are-errors \
	    -no-qml-debug -optimized-qmake -strip -fontconfig -no-sql-sqlite

exit 0

echo ">> Make..."
make

echo ">> Make Install..."
make install
