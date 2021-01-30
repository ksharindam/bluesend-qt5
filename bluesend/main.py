#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import dbus
from dbus.exceptions import DBusException
from dbus.mainloop.pyqt5 import DBusQtMainLoop

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDialog, QGridLayout, QTableView, QDialogButtonBox,
                        QAbstractItemView, QTableWidget, QHeaderView, QTableWidgetItem,
                        QWidget, QMessageBox, QProgressBar, QLabel)

sys.path.append(os.path.dirname(__file__))
import resources_rc

BUS_NAME = 'org.bluez.obex'
OBEX_PATH = '/org/bluez/obex'

# python3 always returns str instead of QString
# convert byte string to unicode str
#utf8 = lambda x : x.decode('utf-8')
def extract_uuids(uuid_list):
    uuids = []
    for uuid in uuid_list:
        if (uuid.endswith("-0000-1000-8000-00805f9b34fb")):
            if (uuid.startswith("0000")):
                val = "0x" + uuid[4:8]
            else:
                val = "0x" + uuid[0:8]
        else:
            val = str(uuid)
        uuids.append(val)
    return uuids



class DeviceDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.setupUi()
        self.device_dict = {}
        self.getDevices()
        self.updateDeviceTable()

    def setupUi(self):
        self.setWindowTitle("Bluetooth Devices")
        self.resize(328, 275)
        self.gridLayout = QGridLayout(self)
        # set up device list table
        self.tableView = QTableWidget(0, 1, self)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows) # Select Rows
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        #self.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView.horizontalHeader().setHidden(True)
        self.tableView.verticalHeader().setHidden(True)
        self.gridLayout.addWidget(self.tableView, 0, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.tableView.cellDoubleClicked.connect(self.accept)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def updateDeviceTable(self):
        self.tableView.setRowCount(len(self.device_dict))
        for row, text in enumerate (self.device_dict.values()):
            title_item = QTableWidgetItem(text)
            self.tableView.setItem(row, 0, title_item)

    def selectedDeviceAddress(self):
        row = self.tableView.selectionModel().selectedRows()[0].row()
        return list(self.device_dict.keys())[row]

    def getDevices(self):
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object("org.bluez", "/"),
                                "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()

        devices = []
        for path, interfaces in objects.items():
            if "org.bluez.Device1" in interfaces:
                devices.append(str(path))
            elif "org.bluez.Adapter1" in interfaces:
                adapter_path = str(path)

        for dev_path in devices:

            dev = objects[dev_path]
            properties = dev["org.bluez.Device1"]

            uuids = extract_uuids(properties["UUIDs"])
            if "0x1105" not in uuids: # does not support OBEX Object Push
                continue
            address = str(properties["Address"])
            alias = str(properties["Alias"])
            self.device_dict[address] = alias

        bus.add_signal_receiver(self.onInterfacesAdded,
                dbus_interface = "org.freedesktop.DBus.ObjectManager",
                signal_name = "InterfacesAdded")

        self.adapter = dbus.Interface(bus.get_object("org.bluez", adapter_path),
                                    'org.bluez.Adapter1')
        self.adapter.StartDiscovery()

    def onInterfacesAdded(self, path, interfaces):
        if "org.bluez.Device1" not in interfaces:
            return
        properties = interfaces["org.bluez.Device1"]

        print("Device Added")
        uuids = extract_uuids(properties["UUIDs"])
        if "0x1105" not in uuids: # does not support OBEX Object Push
            return

        address = str(properties["Address"])
        if address in self.device_dict:
            return
        alias = str(properties["Alias"])
        self.device_dict[address] = alias
        row = self.tableView.rowCount()
        self.tableView.insertRow(row)
        title_item = QTableWidgetItem(alias)
        self.tableView.setItem(row, 0, title_item)

    def accept(self):
        if len(self.tableView.selectedItems()) == 0:
            return
        self.adapter.StopDiscovery()
        QDialog.accept(self)

    def reject(self):
        self.adapter.StopDiscovery()
        QDialog.reject(self)


class Window(QMainWindow):
    def __init__(self, filenames):
        QMainWindow.__init__(self)
        self.setupUi()
        self.completed_size = 0 # total size of the finished files
        self.allfiles_size = 0 # total size of all files selected
        self.transfer_path = None
        self.filenames = filenames
        self.status_active = False

        self.tableView.setRowCount(len(self.filenames))
        for row, filename in enumerate (self.filenames):
            item = QTableWidgetItem(os.path.basename(filename))
            item.setIcon( QIcon(':/document.png') )
            self.tableView.setItem(row, 0, item)
            self.allfiles_size += os.path.getsize(filename)

        self.show()

        dlg = DeviceDialog(self)
        if (dlg.exec_()==QDialog.Accepted):
            dev_addr = dlg.selectedDeviceAddress()
            self.sendFiles(dev_addr)

    def setupUi(self):
        self.setWindowTitle("Bluetooth : Send File")
        self.resize(328, 275)
        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.gridLayout = QGridLayout(self.centralwidget)
        self.tableView = QTableWidget(0, 1, self.centralwidget)
        # Add Progress Bar
        self.progressBar = QProgressBar(self)
        self.progressBar.hide()
        # Add status label
        self.statusbar = QLabel(self)
        # Add ButtonBox
        self.buttonBox = QDialogButtonBox(self.centralwidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        # Add widgets to grid layout
        self.gridLayout.addWidget(self.tableView, 0, 0, 1, 2)
        self.gridLayout.addWidget(self.progressBar, 1, 0, 1, 2)
        self.gridLayout.addWidget(self.statusbar, 2, 0, 1, 1)
        self.gridLayout.addWidget(self.buttonBox, 2, 1, 1, 1)
        #setup table
        self.tableView.horizontalHeader().setHidden(True)
        self.tableView.verticalHeader().setHidden(True)
        self.tableView.setAlternatingRowColors(True)
        #self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows) # Select Rows
        self.tableView.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableView.setTextElideMode(QtCore.Qt.ElideMiddle)

        self.buttonBox.rejected.connect(self.close)

    def sendFiles(self, dev_addr):
        if (len(self.filenames)==0):
            return
        bus = dbus.SessionBus()
        self.client = dbus.Interface(bus.get_object(BUS_NAME, OBEX_PATH), 'org.bluez.obex.Client1')
        try:
            session_path = self.client.CreateSession(dev_addr, { "Target": "OPP" })
        except DBusException as e:
            msg = "%s\n%s" % (e.get_dbus_name(), e.get_dbus_message())
            QMessageBox.critical(self, "Error !", msg)
            return
        obj = bus.get_object(BUS_NAME, session_path)
        self.session = dbus.Interface(obj, 'org.bluez.obex.Session1')
        self.opp = dbus.Interface(obj, 'org.bluez.obex.ObjectPush1')
        bus.add_signal_receiver(self.onPropertiesChange,
                                dbus_interface="org.freedesktop.DBus.Properties",
                                signal_name="PropertiesChanged",
                                path_keyword="path")
        self.opp.SendFile(self.filenames[0],
                            reply_handler=self.create_transfer_reply,
                            error_handler=self.error)
        self.status_active = True
        self.current_index = 0

    def create_transfer_reply(self, path, properties):
        ''' Callback when transfer is started '''
        self.transfer_path = path
        self.transfer_size = properties["Size"]
        self.transferred = 0 # tranferred amount of current file
        self.progressBar.show()

    def error(self, err):
        print(err)

    def onPropertiesChange(self, interface, properties, invalidated, path):
        if path != self.transfer_path:
            return

        status = properties.get("Status", None)

        if status == "error":
            self.status_active = False
            self.progressBar.hide()
            self.statusbar.setText("Transfer Stopped !")
            self.setWindowTitle("Bluetooth : Send File")
            return

        if "Transferred" in properties:
            value = properties["Transferred"]
            speed = (value - self.transferred) / 1024
            self.statusbar.setText("%d kB/s" % speed)
            progress = 100*(self.completed_size+value)/self.allfiles_size
            self.progressBar.setValue(progress)
            self.setWindowTitle("Sending File (%d%%)" % progress)
            self.transferred = value

        if status=="complete":
            #print("Transfer : complete")
            item = self.tableView.item(self.current_index, 0)
            item.setIcon( QIcon(':/dialog-ok-apply.png') )
            self.statusbar.setText("0 kB/s")
            self.completed_size += self.transfer_size
            self.current_index += 1
            if self.current_index < len(self.filenames):
                self.opp.SendFile(self.filenames[self.current_index],
                            reply_handler=self.create_transfer_reply,
                            error_handler=self.error)
                self.status_active = True
            else:
                self.close()

    def closeEvent(self, ev):
        if self.status_active:
            self.client.RemoveSession(self.session)
        QMainWindow.closeEvent(self, ev)



def main():
    app = QApplication(sys.argv)
    DBusQtMainLoop(set_as_default=True)

    filenames = []
    if len(sys.argv)>1 :
        for path in sys.argv[1:]:
            if os.path.exists(path):
                filenames.append(os.path.abspath(path))

    win = Window(filenames)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
