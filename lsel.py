import wx

class NonFocusableListCtrl(wx.ListCtrl):
	def AcceptsFocus(self):
		return False

class MyApp(wx.App):
	def OnInit(self):
		self.frame = MyFrame(parent=None, title="Highlight Text from ListCtrl Selection")
		self.frame.Show()
		return True

class MyFrame(wx.Frame):
	def __init__(self, *args, **kwargs):
		super(MyFrame, self).__init__(*args, **kwargs)

		self.panel = wx.Panel(self)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		
		# Use our custom ListCtrl
		self.listctrl = NonFocusableListCtrl(self.panel, style=wx.LC_REPORT)
		self.listctrl.InsertColumn(0, 'Word to Highlight')
		words = ["Hello", "world", "wxPython", "ListCtrl"]
		for word in words:
			self.listctrl.InsertItem(0, word)
		self.listctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
		
		# TextCtrl setup remains the same
		self.textctrl = wx.TextCtrl(self.panel, value="Hello world! wxPython is great. ListCtrl is useful.", style=wx.TE_MULTILINE)
		
		self.sizer.Add(self.listctrl, 1, wx.EXPAND)
		self.sizer.Add(self.textctrl, 1, wx.EXPAND)
		
		self.panel.SetSizer(self.sizer)
		self.sizer.Fit(self)

	def on_item_selected(self, event):
		word_to_highlight = self.listctrl.GetItemText(event.GetIndex())
		
		def do_highlight():
			content = self.textctrl.GetValue()
			start_pos = content.find(word_to_highlight)
			
			if start_pos != -1:
				end_pos = start_pos + len(word_to_highlight)
				self.textctrl.SetFocus()
				self.textctrl.SetSelection(start_pos, end_pos)

		# Delay the highlighting using a timer
		wx.CallLater(100, do_highlight)

if __name__ == "__main__":
	app = MyApp()
	app.MainLoop()
