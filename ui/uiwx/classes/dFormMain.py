''' dFormMain.py '''
import wx
from dFormMixin import dFormMixin
from dMainMenuBar import dMainMenuBar

# Different platforms expect different frame types. Notably,
# most users on Windows expect and prefer the MDI parent/child
# type frames.
if wx.Platform == '__WXMSW__':      # Microsoft Windows
    wxFrameClass = wx.MDIParentFrame
else:
    wxFrameClass = wx.Frame

class dFormMain(wxFrameClass, dFormMixin):
    def __init__(self, dApp=None):
        wxFrameClass.__init__(self, None, -1, "dFormMain")
        self.SetName("dFormMain")
        self.SetSize((640,480))
        self.SetPosition((0,0))
        dFormMixin.__init__(self, dApp)
        self.CreateStatusBar()
        self.SetMenuBar(dMainMenuBar(self))
      
        if self.dApp:
            self.SetStatusText("Welcome to %s" % self.dApp.getAppInfo("appName"))
            self.SetLabel("%s Version %s" % (self.dApp.getAppInfo("appName"),
                                             self.dApp.getAppInfo("appVersion")))
        else:
            self.SetLabel("Dabo")
            self.SetStatusText("Welcome to Dabo!")
        
        
    def statusMessage(self, message=""):
        statusBar = self.GetStatusBar()
        try:
            statusBar.PopStatusText()
        except:
            pass
        statusBar.PushStatusText(message)
        statusBar.Update()    # Refresh() doesn't work, and this is only needed sometimes.
    
 
        
if __name__ == "__main__":
    import test
    test.Test().runTest(dFormMain)
