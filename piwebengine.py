#!/usr/bin/env python
#
#  Build QT5 webengine
#

import os
import sys
import xsysroot

if __name__ == '__main__':

    # You want to be careful to enable a debug build. libQtWebengine.so takes 817MB :-)
    debug_build=False
    build_mode='release' if not debug_build else 'debug'

    # We need a xsysroot profile with QT5 built in it
    if len(sys.argv) > 1:
        xprofile=sys.argv[1]
    else:
        print 'Need a xsysroot profile'
        sys.exit(1)

    # Find and activate the xsysroot profile
    print '>>> Opening xsysroot profile: {}'.format(xprofile)
    try:
        picute=xsysroot.XSysroot(profile=xprofile)
    except:
        print 'You need to create a Xsysroot Picute profile'
        print 'Please see the README file'
        sys.exit(1)

    # Locate Webengine source code directory
    webengine_path=os.path.join(picute.query('tmp'), 'qt5/qtwebengine')

    # Apply temporary patch to build QT5.7 Webengine for the RPI
    # https://bugreports.qt.io/browse/QTBUG-57037
    if not os.path.isdir(webengine_path):
           print '>>> Could not find Webengine path: {}'.format(webengine_path)
           sys.exit(1)
    else:
        patch_file='gyp_run.pro'
        print '>>> Overwriting webengine qmake file: {}'.format(patch_file)
        rc=os.system('cp {} {}/src/core'.format(patch_file, webengine_path))
        if rc:
            print 'Could not apply patch'
            sys.exit(1)
        else:
            print '>>> Webengine patch has been applied'

    # Now mount image if needed
    print '>>> Accessing image...'
    if not picute.is_mounted():
        if not picute.mount():
            sys.exit(1)

    # Step 1: QMAKE
    print '>>> Running Qmake...'
    cmdline_prefix='export PKG_CONFIG_PATH={}/usr/lib/arm-linux-gnueabihf/pkgconfig'.format(picute.query('sysroot'))
    print '>>> cmdline_prefix: ', cmdline_prefix
    qmake_command='{}/usr/local/qt5/bin/qmake ' \
        'WEBENGINE_CONFIG+=use_proprietary_codecs CONFIG+={}'.format(picute.query('sysroot'), build_mode)
    print '>>> Qmake command:', qmake_command
    rc=os.system('{} ; cd {} ; {}'.format(cmdline_prefix, webengine_path, qmake_command))
    if rc:
        print '>>> Qmake failed rc={} :-('.format(rc)
        sys.exit(1)

    # Step 2: MAKE
    print '>>> Running Make...'
    rc=os.system('{} ; cd {} ; make'.format(cmdline_prefix, webengine_path))
    if rc:
        print '>>> Make failed rc={} :-('.format(rc)
        sys.exit(1)

    # Step 3: INSTALL
    print '>>> Running Make Install...'
    rc=os.system('cd {} ; sudo make install'.format(webengine_path))
    if rc:
        print '>>> Make install failed rc={} :-('.format(rc)
        sys.exit(1)

    print '>>> Webengine built and installed'

    # Webengine build complete: Unmount image
    if not picute.umount():
        print '>>> WARNING: Image is busy, most likely installation left some running processes.'
        sys.exit(1)

    sys.exit(0)
