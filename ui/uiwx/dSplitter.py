import random
import wx
import dabo
dabo.ui.loadUI("wx")
import dForm
import dabo.dEvents as dEvents
from dabo.dLocalize import _
import dabo.dColors as dColors
import dControlMixin as cm
from dabo.ui import makeDynamicProperty


class SplitterPanelMixin:
	def __init__(self, parent, *args, **kwargs):
		if self.ShowSplitMenu:
			self.bindEvent(dEvents.ContextMenu, self._onMixinContextMenu)
	
	
	def _onMixinContextMenu(self, evt):
		evt.stop()
		sm = dabo.ui.dMenu(self)
		sm.append("Split this pane", bindfunc=self.onSplit)
		if self.Parent.canRemove(self):
			sm.append("Remove this pane", bindfunc=self.onRemove)
		if self.Parent.IsSplit():
			sm.append("Switch Orientation", bindfunc=self.onFlipParent)
		self.showContextMenu(sm)
		

	def onSplit(self, evt):
		self.split()
		
		
	def onRemove(self, evt):
		self.remove()
	
	
	def onFlipParent(self, evt):
		ornt = self.Parent.Orientation
		self.Parent.Orientation = ("H", "V")[ornt.startswith("H")]
		
	
	def remove(self):
		self.Parent.remove(self)
		
		
	def split(self, dir_=None):
		if not self.Parent.IsSplit():
			# Re-show the hidden split panel
			self.Parent.split()
			return
		orientation = self.Parent.Orientation[0].lower()
		# Default to the opposite of the current orientation
		if orientation == "h":
			newDir = "v"
		else:
			newDir = "h"
		if self.Sizer is None:
			self.Sizer = dabo.ui.dSizer(newDir)
		if dir_ is None:
			dir_ = newDir
		win = dSplitter(self, createPanes=True)
		win.Orientation = dir_
		win.unsplit()
		win.split()
		self.Sizer.append(win, 1, "expand")
		self.splitter = win
		self.Layout()
		
	
	def unsplit(self, win=None):
		self.splitter.unsplit(win)
	
	
	# Property definitions start here
	def _getShowSplitMenu(self):
		try:
			ret = self._showSplitMenu
		except AttributeError:
			ret = self._showSplitMenu = True
		return ret

	def _setShowSplitMenu(self, val):
		if self._constructed():
			self._showSplitMenu = val
			if val:
				self.bindEvent(dEvents.ContextMenu, self._onContextMenu)
			else:
				self.unbindEvent(dEvents.ContextMenu)
		else:
			self._properties["ShowSplitMenu"] = val


	ShowSplitMenu = property(_getShowSplitMenu, _setShowSplitMenu, None,
			_("Determines if the Split/Unsplit context menu is shown (default=True)  (bool)"))
	
		

		
class dSplitter(cm.dControlMixin, wx.SplitterWindow):
	""" Main class for handling split windows. It will contain two
	panels (subclass of SplitterPanelMixin), each of which can further 
	split itself in two.
	"""
	def __init__(self, parent, properties=None, *args, **kwargs):
		self._baseClass = dSplitter
		baseStyle = wx.SP_3D | wx.SP_PERMIT_UNSPLIT
		style = self._extractKey((kwargs, properties), "style", baseStyle)
		self._createPanes = self._extractKey((kwargs, properties), "createPanes", False)
		self._splitOnInit = self._extractKey((kwargs, properties), "splitOnInit", self._createPanes)
		# Default to a decent minimum panel size if none is specified
		mp = self._extractKey((kwargs, properties), "MinimumPanelSize", 20)
		kwargs["MinimumPanelSize"] = mp
			
		# Default to vertical split
		self._orientation = "v"
		self._sashPos = 100
		self._p1 = self._p2 = None
		# Default to showing the context menus on the panels
		self._showPanelSplitMenu = True

		preClass = wx.PreSplitterWindow
		cm.dControlMixin.__init__(self, preClass, parent, properties, 
				style=style, *args, **kwargs)
		
	
	def _initEvents(self):
		super(dSplitter, self)._initEvents()
		self.Bind(wx.EVT_SPLITTER_DCLICK, self._onSashDClick)
		self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self._onSashPos)


	def _afterInit(self):
		# Create the panes
		if self._createPanes:
			self.createPanes()
		if self._splitOnInit:
			self.split()
		super(dSplitter, self)._afterInit()

	
	def _makeSplitterPanelClass(self, cls):
		mixin = SplitterPanelMixin
		if hasattr(self.Form, "isDesignerForm"):
			mixin = self.Application.getControlClass(mixin)		
		# See if the class already is mixed in with the SplitterPanelMixin
		if isinstance(cls, mixin):
			ret = cls
		else:
			class MixedSplitterPanel(cls, mixin):
				def __init__(self, parent, *args, **kwargs):
					cls.__init__(self, parent, *args, **kwargs)
					mixin.__init__(self, parent, *args, **kwargs)
			ret = MixedSplitterPanel
		return ret


	def createPanes(self, cls=None, pane=None, force=False):
		if cls is None:
			cls = self.PanelClass
		spCls = self._makeSplitterPanelClass(cls)
		if pane is None:
			p1 = p2 = True
		else:
			p1 = (pane == 1)
			p2 = (pane == 2)
		if p1 and (force or self.Panel1 is None):
			self.Panel1 = spCls(self)
		if p2 and (force or self.Panel2 is None):
			self.Panel2 = spCls(self)
	
	
	def initialize(self, pnl):
		self.Initialize(pnl)
	
	
	def _onSashDClick(self, evt):
		""" Handle the double-clicking of the sash. This will call
		the user-customizable onSashDClick() method.
		"""
		## Vetoing the event now will give user code the opportunity to not do the
		## default of removing the sash, by calling evt.stop().
		evt.Veto()
		# Update the internal sash position attribute.
		self._getSashPosition()
		# Raise a dEvent for other code to bind to,
		self.raiseEvent(dEvents.SashDoubleClick, evt)
		
		
	def _onSashPos(self, evt):
		"""Fires when the sash position is changed."""
		evt.Skip()
		# Update the internal sash position attribute.
		self._getSashPosition()
		# Raise a dEvent for other code to bind to,
		self.raiseEvent(dEvents.SashPositionChanged, evt)
	
		
	def split(self, dir_=None):
		if self.IsSplit():
			return
		if self.Panel1 is None or self.Panel2 is None:
			# No panels, so we can't split! Create them.
			self.createPanes()
			
		if dir_:
			self.Orientation = dir_
		# Get the position
		pos = self.SashPosition
		if self.Orientation == "Horizontal":
			self.SplitHorizontally(self.Panel1, self.Panel2, pos)
		else:
			self.SplitVertically(self.Panel1, self.Panel2, pos)
		self.Layout()
	
	
	def unsplit(self, win=None):
		if self.IsSplit():
			# Save the sash position
			self._getSashPosition()
			self.Unsplit(win)
			self.Layout()
			
	
	def canRemove(self, pnl):
		ret = self.IsSplit()
		if not ret:
			# Make sure that there is at least one level of splitting somewhere
			obj = self
			while obj.Parent and not ret:
				obj = obj.Parent
				if isinstance(obj, dSplitter):
					ret = self.IsSplit()
		return ret
		
		
	def remove(self, pnl):
		if self.IsSplit():
			self.unsplit(pnl)
		else:
			# If the parent of this is a SplitterPanelMixin, tell it to hide
			prnt = self.Parent
			if isinstance(prnt, SplitterPanelMixin):
				prnt.remove()
			else:
				self.Destroy()				
	
	
	def toggleSplit(self):
		"""Flips the split status of the control."""
		if self.IsSplit():
			self.unsplit()
		else:
			self.split()
			
				
	def _getMinPanelSize(self):
		return self.GetMinimumPaneSize()
		
	def _setMinPanelSize(self, val):
		if self._constructed():
			self.SetMinimumPaneSize(val)
		else:
			self._properties["MinimumPanelSize"] = val
		
	
	def _getOrientation(self):
		if self._orientation[0].lower() == "v":
			return "Vertical"
		else:
			return "Horizontal"
			
	def _setOrientation(self, val):
		if self._constructed():
			orient = val.lower()[0]
			if orient in ("h", "v"):
				self._orientation = {"h": "Horizontal", "v": "Vertical"}[orient]
				if self.IsSplit():
					self.lockDisplay()
					self.unsplit()
					self.split()
					self.unlockDisplay()
			else:
				raise ValueError, "Orientation can only be 'Horizontal' or 'Vertical'"
		else:
			self._properties["Orientation"] = val
	
	
	def _getPanel1(self):
		return self._p1
		
	def _setPanel1(self, pnl):
		if self._constructed():
			old = self._p1
			if self.IsSplit():
				if self.Orientation == "Vertical":
					self.SplitVertically(pnl, self._p2)
				else:
					self.SplitHorizontally(pnl, self._p2)
			else:
				self.Initialize(pnl)
			self._p1 = pnl
			try:
				old.Destroy()
			except:
				pass
		else:
			self._properties["Panel1"] = pnl
			

	def _getPanel2(self):
		return self._p2
		
	def _setPanel2(self, pnl):
		if self._constructed():
			old = self._p2
			self._p2 = pnl
			if self.IsSplit():
				self.ReplaceWindow(self.GetWindow2(), pnl)
			try:
				old.Destroy()
			except:
				pass
		else:
			self._properties["Panel2"] = pnl
			
	
	def _getPanelClass(self):
		try:
			ret = self._panelClass
		except:
			ret = self._panelClass = dabo.ui.dPanel
		return ret
		
	def _setPanelClass(self, val):
		self._panelClass = val
		

	def _getSashPosition(self):
		if self.IsSplit():
			self._sashPos = self.GetSashPosition()
		return self._sashPos
		
	def _setSashPosition(self, val):
		if self._constructed():
			self.SetSashPosition(val)
			# Set the internal prop from the wx Prop
			self._sashPos = self.GetSashPosition()
		else:
			self._properties["SashPosition"] = val

	
	def _getShowPanelSplitMenu(self):
		return self._showPanelSplitMenu

	def _setShowPanelSplitMenu(self, val):
		if self._constructed():
			self._showPanelSplitMenu = val
			try:
				self.Panel1.ShowSplitMenu = val
			except: pass
			try:
				self.Panel2.ShowSplitMenu = val
			except: pass
		else:
			self._properties["ShowPanelSplitMenu"] = val


	def _getSplit(self):
		return self.IsSplit()

	def _setSplit(self, val):
		if val:
			self.split()
		else:
			self.unsplit()


	MinimumPanelSize = property(_getMinPanelSize, _setMinPanelSize, None,
			_("Controls the minimum width/height of the panels.  (int)"))

	Orientation = property(_getOrientation, _setOrientation, None,
			_("Determines if the window splits Horizontally or Vertically.  (string)"))

	Panel1 = property(_getPanel1, _setPanel1, None,
			_("Returns the Top/Left panel.  (dPanel)"))

	Panel2 = property(_getPanel2, _setPanel2, None,
			_("Returns the Bottom/Right panel.  (dPanel)"))

	PanelClass = property(_getPanelClass, _setPanelClass, None,
			_("""Class used for creating panels. If the class does not descend from 
			SplitterPanelMixin, that class will be mixed-into the class specified here. 
			This must be set before the panels are created; setting it afterward has 
			no effect unless you destroy the panels and re-create them.  
			Default=dPanel  (dPanel)"""))
			
	SashPosition = property(_getSashPosition, _setSashPosition, None,
			_("Position of the sash when the window is split.  (int)"))

	ShowPanelSplitMenu = property(_getShowPanelSplitMenu, _setShowPanelSplitMenu, None,
			_("""Determines if the default context menu for split/unsplit is enabled 
			for the panels (default=True)  (bool)"""))
	
	Split = property(_getSplit, _setSplit, None,
			_("Returns the split status of the control  (bool)"))


	DynamicMinimumPanelSize = makeDynamicProperty(MinimumPanelSize)
	DynamicOrientation = makeDynamicProperty(Orientation)
	DynamicPanel1 = makeDynamicProperty(Panel1)
	DynamicPanel2 = makeDynamicProperty(Panel2)
	DynamicSashPosition = makeDynamicProperty(SashPosition)
	DynamicSplit = makeDynamicProperty(Split)
	


class _dSplitter_test(dSplitter):
	def __init__(self, *args, **kwargs):
		kwargs["createPanes"] = True
		super(_dSplitter_test, self).__init__(*args, **kwargs)

	def initProperties(self):
		self.Width = 250
		self.Height = 200
		self.MinimumPanelSize = 20

	def afterInit(self):
		self.Panel1.BackColor = random.choice(dColors.colorDict.values())
		self.Panel2.BackColor = random.choice(dColors.colorDict.values())
		

	def onSashDoubleClick(self, evt):
		if not dabo.ui.areYouSure("Remove the sash?"):
			evt.stop()


if __name__ == "__main__":
	import test
	test.Test().runTest(_dSplitter_test)
