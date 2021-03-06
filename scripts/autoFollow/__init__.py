import ts3lib, ts3defines, datetime
from ts3plugin import ts3plugin
from PythonQt.QtCore import QTimer


class autoFollow(ts3plugin):
    name = "Anti Follow (former Love Plugin)"
    apiVersion = 22
    requestAutoload = True
    version = "1.0"
    author = "Bluscream"
    description = "Auto Follow specified users around."
    offersConfigure = False
    commandKeyword = ""
    infoTitle = None
    menuItems = [(ts3defines.PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL, 0, "Toggle " + name, "")]
    hotkeys = []
    enabled = False
    debug = False
    whitelistUIDs = [""]
    whitelistSGIDs = [2]
    delay = 0
    defaultPassword = "123"
    schid=0;clid=0;cid=0;

    @staticmethod
    def timestamp(): return '[{:%Y-%m-%d %H:%M:%S}] '.format(datetime.now())

    def __init__(self):
        if self.debug: ts3lib.printMessageToCurrentTab("{0}[color=orange]{1}[/color] Plugin for pyTSon by [url=https://github.com/{2}]{2}[/url] loaded.".format(self.timestamp(), self.name, self.author))

    def onMenuItemEvent(self, schid, atype, menuItemID, selectedItemID):
        if atype == ts3defines.PluginMenuType.PLUGIN_MENU_TYPE_GLOBAL and menuItemID == 0:
            self.enabled = not self.enabled
            ts3lib.printMessageToCurrentTab("{0}Set {1} to [color=yellow]{2}[/color]".format(self.timestamp(),self.name,self.enabled))

    def onClientMoveMovedEvent(self, schid, clientID, oldChannelID, newChannelID, visibility, moverID, moverName, moverUniqueIdentifier, moveMessage):
        (err, ownID) = ts3lib.getClientID(schid)
        if clientID != ownID or moverID == ownID: return
        (err, sgids) = ts3lib.getClientVariable(schid, clientID, ts3defines.ClientPropertiesRare.CLIENT_SERVERGROUPS)
        if set(sgids).isdisjoint(self.whitelistSGIDs): return
        (err, uid) = ts3lib.getClientVariable(schid, clientID, ts3defines.ClientProperties.CLIENT_UNIQUE_IDENTIFIER)
        if uid in self.whitelistUIDs: return
        self.schid=schid;self.clid=ownID;self.cid=oldChannelID
        if self.delay >= 0: QTimer.singleShot(self.delay, self.moveBack)
        else: self.moveBack()


    def moveBack(self):
        ts3lib.requestClientMove(self.schid, self.clid, self.cid, self.defaultPassword)
        self.schid = 0;self.clid = 0;self.cid = 0
