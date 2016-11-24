#!/usr/bin/env python
#
#  The MIT License (MIT)
#
#  Copyright (c) 2016 Albert Casals - albert@mitako.eu
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
#
#  picute.py
#
#  Program that builds QT5.5 on pipaOS 4.4 XGUI version.
#
#  See the README for details.
#

import os
import sys
import time
import platform
import multiprocessing

import xsysroot

# Release version
__version__='1.10'


def test_image(picute, install_path):
    '''
    Performs minimalist tests on the built image
    '''
    failed=0
    sysroot=picute.query('sysroot')
    qt5_dir='{}/{}'.format(sysroot, install_path)
    qt5_qmake=os.path.join(qt5_dir, 'bin/qmake')
    qt5_wayland_dir=os.path.join(qt5_dir, 'include/QtWaylandClient')
    qt5_wayland_so=os.path.join(qt5_dir, 'lib/libQt5WaylandClient.so.5')
    wayland_scanner=os.path.join(qt5_dir, 'bin/qtwaylandscanner')

    if not os.path.isdir(qt5_dir):
        failed+=1
        print 'FAILED: qt5 dir not found: {}'.format(qt5_dir)
    if not os.path.isfile(qt5_qmake):
        failed+=1
        print 'FAILED: qmake not found: {}'.format(qt5_dir)
    if not os.path.isdir(qt5_wayland_dir):
        failed+=1
        print 'FAILED: qtwayland lib directory: {}'.format(qt5_wayland_dir)
    if not os.path.isfile(qt5_wayland_so):
        failed+=1
        print 'FAILED: could not find QtWayland .so: {}'.format(qt5_wayland_so)
    if not os.path.isfile(wayland_scanner):
        failed+=1
        print 'FAILED: could not find Qt Wayland scanner: {}'.format(wayland_scanner)

    return failed


def baptize_image(picute):
    '''
    Prepare the image for the first time. yay!!
    '''

    # make sure the image is not currently in use
    if picute.is_mounted():
        if not picute.umount():
            return False

    # renew the image so we start from clean
    if not picute.renew():
        return False
    else:
        # once renewed, expand it to grow in size, qt5 wouldn't fit
        picute.umount()
        if not picute.expand():
            print 'error expanding image size to {}'.format(picute.query('qcow_size'))
            return False
        else:
            picute.mount()

    # baptize the picute version
    picute.edfile('/etc/picute_version', 'picute v{} - {}'.format(__version__, time.ctime()))

    # set the system hostname
    picute_hostname='picute'
    picute_hosts_file='/etc/hosts'
    picute.edfile('/etc/hostname', picute_hostname)
    picute.edfile(picute_hosts_file, '127.0.0.1 localhost')
    picute.edfile(picute_hosts_file, '127.0.0.1 {}'.format(picute_hostname), append=True)

    # custom firmware config.txt settings
    src_config_txt='config.txt'
    dst_config_txt=os.path.join(picute.query('sysboot'), src_config_txt)
    rc=os.system('sudo cp -fv {} {}'.format(src_config_txt, dst_config_txt))
    if rc:
        print 'WARNING: could not copy config.txt rc={}'.format(rc)

    # custom kernel boot parameters
    src_cmdline='cmdline.txt'
    dst_cmdline=os.path.join(picute.query('sysboot'), src_cmdline)
    rc=os.system('sudo cp -fv {} {}'.format(src_cmdline, dst_cmdline))
    if rc:
        print 'WARNING: could not copy cmdline rc={}'.format(rc)

    # Put the system up to date and install QT5 build dependencies
    # We might need more, for example TLS and further backends
    qt5_builddeps='libc6-dev libxcb1-dev libxcb-icccm4-dev libxcb-xfixes0-dev ' \
        'libxcb-image0-dev libxcb-keysyms1-dev libxcomposite-dev ' \
        'libxcb-sync0-dev libxcb-randr0-dev libx11-xcb-dev libxcb-render-util0-dev ' \
        'libxrender-dev libxext-dev libxcb-glx0-dev pkg-config ' \
        'libssl-dev libraspberrypi-dev libfreetype6-dev libxi-dev libcap-dev ' \
        'libwayland-dev libxkbcommon-dev build-essential git-core libfontconfig1-dev ' \
        'libasound2-dev libinput-dev libmtdev-dev libproxy-dev libdirectfb-dev ' \
        'libts-dev libudev-dev libxcb-xinerama0-dev ' \
        'libdbus-1-dev libicu-dev libglib2.0-dev ' \
        'libavutil-dev=7:3.2-2~bpo8+2 libavcodec-dev=7:3.2-2~bpo8+2 libavformat-dev=7:3.2-2~bpo8+2 ' \
        'libvpx=1.6.0-2~bpo8+1 libopus-dev libopusfile-dev libwebp-dev '
    
    # Webengine specific dependencies (for FFMPEG native build mode) are pulled from Debian ARM backports repo
    picute.edfile('/etc/apt/sources.list.d/raspberrypi-backports.list',
                  'deb http://httpredir.debian.org/debian jessie-backports main contrib')
    picute.execute('apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 8B48AD6246925553')
    picute.execute('apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7638D0442B90D010')

    if picute.execute('apt-get update'):
        return False
    if picute.execute('apt-get install -y --no-install-recommends {}'.format(qt5_builddeps)):
        return False

    # Fix relative symlinks to libdl and libm (so called fixQualifiedPaths in QT jargon)
    # TODO: Use readlink instead of hardcoded destination to .so versioned filename,
    #       but no big deal really. This is a development / builder box.
    picute.execute('rm -fv /usr/lib/arm-linux-gnueabihf/libdl.so')
    picute.execute('cp -fv /lib/arm-linux-gnueabihf/libdl.so.2 /usr/lib/arm-linux-gnueabihf/libdl.so')
    picute.execute('rm -fv /usr/lib/arm-linux-gnueabihf/libm.so')
    picute.execute('cp -fv /lib/arm-linux-gnueabihf/libm.so.6 /usr/lib/arm-linux-gnueabihf/libm.so')

    return True



if __name__ == '__main__':

    help_welcome='Welcome to picute version {} builder'.format(__version__)
    help_syntax=' Syntax: picute.py <xsysroot profile> [--baptize]'
    output_image='picute-{}.img'.format(__version__)
    baptize=False
    wayland=False
    convert_image=False

    # Xsysroot profile name that holds the original pipaOS image
    # (See the file xsysroot.conf for details)
    if len(sys.argv) < 2:
        print help_syntax
        sys.exit(1)
    else:
        xsysroot_profile_name=sys.argv[1]

    print help_welcome

    # Do we want to baptize the image from scratch?
    if len(sys.argv) == 3:
        if sys.argv[2] == '--baptize':
            print 'WARNING: Baptizing image from scratch'
            baptize=True
        else:
            print help_syntax
            sys.exit(1)
                    
    # Find and activate the xsysroot profile
    try:
        picute=xsysroot.XSysroot(profile=xsysroot_profile_name)
    except:
        print 'You need to create a Xsysroot Picute profile'
        print 'Please see the README file'
        sys.exit(1)

    # prepare some commonly used paths and variables
    xtmp=picute.query('tmp')
    host_numcpus=multiprocessing.cpu_count()
    qt5_version='5.7.1'
    qt5_srcdir=os.path.join(xtmp, 'qt5')
    rpi_tools='/opt/rpi-tools'
    qt5_path_prefix='/usr/local/qt5'

    xgcc_path32='/arm-bcm2708/gcc-linaro-arm-linux-gnueabihf-raspbian/bin'
    xgcc_path64='/arm-bcm2708/gcc-linaro-arm-linux-gnueabihf-raspbian-x64/bin'

    # find out if 32 or 64 bit host system
    if platform.architecture()[0] == '64bit':
        xgcc_path=xgcc_path64
    else:
        xgcc_path=xgcc_path32
        
    xgplusplus='{}/{}/arm-linux-gnueabihf-g++'.format(rpi_tools, xgcc_path)

    init_repo_done=os.path.join(xtmp, 'init_repo_done.chk')
    configure_done=os.path.join(xtmp, 'configure_done.chk')
    make_done=os.path.join(xtmp, 'make_done.chk')
    make_install_done=os.path.join(xtmp, 'make_install_done.chk')

    configure_opts='-opengl es2 -eglfs -xcb -device linux-rasp-pi2-g++ ' \
        '-device-option CROSS_COMPILE={}/{} ' \
        '-sysroot {} -opensource -confirm-license -release -skip qtwayland ' \
        '-prefix {} -pkg-config -no-pch -alsa -no-use-gold-linker -qt-xkbcommon ' \
        '-xkb-config-root /usr/share/X11/xkb -skip qtwebengine -skip qtwebview ' \
        '-nomake tests -nomake examples -verbose -no-warnings-are-errors ' \
        '-no-qml-debug -optimized-qmake -strip -fontconfig -no-sql-sqlite'.format(
            rpi_tools, xgcc_path + '/arm-linux-gnueabihf-',
            picute.query('sysroot'), qt5_path_prefix)

    # Start from a clean image
    time_start=time.time()
    if baptize:
        if not baptize_image(picute):
            print 'Error baptizing image'
            sys.exit(1)
    else:
        if not picute.is_mounted():
            if not picute.mount():
                sys.exit(1)

    if not os.path.isfile(xgplusplus):
        print '>>> Checking QT5 build software on the host'
        print 'Could not find the g++ cross compiler at {}'.format(xgplusplus)
        sys.exit(0)

    # Step 1: clone the sources
    if not os.path.isdir(qt5_srcdir):
        print '>>> Cloning QT5 sources'
        rc=os.system('git clone --branch {} git://code.qt.io/qt/qt5.git {}'.format(qt5_version, qt5_srcdir))
        if os.WEXITSTATUS(rc):
            print 'Could not clone QT5 sources rc={} :-('.format(rc)
            sys.exit(1)

    # Step 2: init-repository
    if not os.path.isfile(init_repo_done):
        print '>>> Init repository'
        rc=os.system('cd {} && perl init-repository'.format(qt5_srcdir))
        if os.WEXITSTATUS(rc):
            print 'init-repository failed rc={} :-('.format(rc)
            sys.exit(1)
        else:
            os.system('touch {}'.format(init_repo_done))

    # Step 3: configure
    if not os.path.isfile(configure_done) or baptize:
        print '>>> Configure {}'.format(configure_opts)
        rc=os.system('cd {} && ./configure {}'.format(
            qt5_srcdir, configure_opts))
        if os.WEXITSTATUS(rc):
            print 'configure failed rc={} :-('.format(rc)
            sys.exit(1)
        else:
            os.system('touch {}'.format(configure_done))

    # Step 4: make
    if not os.path.isfile(make_done) or baptize:
        print '>>> Make ...'
        rc=os.system('cd {} && make -j {}'.format(qt5_srcdir, host_numcpus))
        if os.WEXITSTATUS(rc):
            print 'make failed rc={} :-('.format(rc)
            sys.exit(1)
        else:
            if wayland:
                # Now make qtwayland with compositor
                print '>>> QtWayland building...'
                rc1=os.system('cd {}/qtwayland && ../qtbase/bin/qmake CONFIG+=wayland-compositor'.format(qt5_srcdir))
                rc2=os.system('cd {}/qtwayland && make'.format(qt5_srcdir))
                rc3=os.system('cd {}/qtwayland && sudo make install'.format(qt5_srcdir))
                print '>>> QtWayland built: rc1={} rc2={} rc3={}'.format(rc1, rc2, rc3)

            os.system('touch {}'.format(make_done))

    # Step 5: make install
    if not os.path.isfile(make_install_done) or baptize:
        print '>>> Make install...'
        rc=os.system('cd {} && sudo make install'.format(qt5_srcdir))
        if os.WEXITSTATUS(rc):
            print 'make install failed :-('
            sys.exit(1)
        else:
            os.system('touch {}'.format(make_install_done))

    # Step 6: run some basic tests on the image
    print '>>> testing image'
    num_failed_tests = test_image(picute, qt5_path_prefix)
    print '>>> tests complete failed={}'.format(num_failed_tests)


    #
    # TODO:  Step 7 => Build webkit (separate python module?)
    #


    # unmount the image and release it
    print '>>> releasing and cleaning image'
    if not picute.umount():
        print 'WARNING: Image is busy, most likely installation left some running processes, skipping conversion'
        sys.exit(1)
    else:
        picute.zerofree(verbose=False)

    if convert_image:
        # Convert the xsysroot image to a raw format ready to flash and boot
        qcow_image=picute.query('qcow_image')
        print 'Converting image {}...'.format(qcow_image)
        if os.path.isfile(output_image):
            os.unlink(output_image)

        rc = os.system('qemu-img convert {} {}'.format(qcow_image, output_image))

    time_end=time.time()
    print 'Process finished in {} secs - image ready at {}'.format(time_end - time_start, output_image)
    sys.exit(0)
