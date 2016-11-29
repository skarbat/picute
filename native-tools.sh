#!/bin/bash
#
# Script to build QT5 core tools natively
# It is executed by "packageme" script
#

if [ `uname -m` != "armv7l" ]; then
    echo "Not running in emulated ARM mode - aborting"
    exit 1
fi

cd /tmp/qt5-native/qtbase
./configure -device linux-rasp-pi2-g++ \
	    -device-option CROSS_COMPILE=/usr/bin/ \
	    -opensource -confirm-license -release \
	    -prefix /usr/local/qt5 -pkg-config -no-pch \
	    -no-use-gold-linker -xkb-config-root /usr/share/X11/xkb \
	    -nomake tests -nomake examples -verbose -no-warnings-are-errors \
	    -no-qml-debug -optimized-qmake -strip -fontconfig -no-sql-sqlite


