#!/usr/bin/python3

##
# Copyright © 2021 Red Hat, Inc
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
##

import re
import signal
import dbus
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

DBusGMainLoop(set_as_default=True)
Gst.init(None)

loop = GLib.MainLoop()

bus = dbus.SessionBus()
request_iface = 'org.freedesktop.portal.Request'
camera_iface = 'org.freedesktop.portal.Camera'

pipeline = None

def terminate():
    if pipeline is not None:
        self.player.set_state(Gst.State.NULL)
    loop.quit()

request_token_counter = 0
sender_name = re.sub(r'\.', r'_', bus.get_unique_name()[1:])

def new_request_path():
    global request_token_counter
    request_token_counter = request_token_counter + 1
    token = 'u%d'%request_token_counter
    path = '/org/freedesktop/portal/desktop/request/%s/%s'%(sender_name, token)
    return (path, token)

def camera_call(method, callback, *args, options={}):
    (request_path, request_token) = new_request_path()
    bus.add_signal_receiver(callback,
                            'Response',
                            request_iface,
                            'org.freedesktop.portal.Desktop',
                            request_path)
    options['handle_token'] = request_token
    print('request token: %s, path: %s'%(request_token, request_path))
    return method(*(args + (options, )),
                  dbus_interface=camera_iface)

def on_gst_message(bus, message):
    type = message.type
    if type == Gst.MessageType.EOS or type == Gst.MessageType.ERROR:
        terminate()

def open_pipewire_remote():
    fd_object = portal.OpenPipeWireRemote({},
                  dbus_interface=camera_iface)
    fd = fd_object.take()
    pipeline = Gst.parse_launch('pipewiresrc fd=%d ! videoconvert ! xvimagesink'%(fd))
    print("playing")
    pipeline.set_state(Gst.State.PLAYING)
    pipeline.get_bus().connect('message', on_gst_message)

def on_access_camera_response(response, results):
    if response != 0:
        print("Failed to access: %s"%response)
        terminate()
        return

    open_pipewire_remote()

portal = bus.get_object('org.freedesktop.portal.Desktop',
                        '/org/freedesktop/portal/desktop')

camera_call(portal.AccessCamera, on_access_camera_response)

try:
    loop.run()
except KeyboardInterrupt:
    terminate()
