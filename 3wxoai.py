import os, time, json
from os.path import join, isfile, basename
import wx
from wxasync import AsyncBind, WxAsyncApp, StartCoroutine
import aiohttp
import asyncio
import openai
from pprint import pprint as pp

openai.api_key = os.getenv("OPENAI_API_KEY")

def timer_decorator(func):
	async def wrapper(instance, *args, **kwargs):  # Add an 'instance' argument
		start_time = time.perf_counter()
		result = await func(instance, *args, **kwargs)
		end_time = time.perf_counter()
		run_time = end_time - start_time
		instance.timer_output.SetLabel(f"{run_time:.4f} sec")
		return result
	return wrapper



# ... [Previous imports remain unchanged]

class MyFrame(wx.Frame):
	def __init__(self):
		super(MyFrame, self).__init__(None, title="OpenAI Chat App", size=(1000, 800))
		
		self.splitter = wx.SplitterWindow(self)
		self.questions_dir='questions'
		# Panel for TreeCtrl (left side)
		self.tree_panel = wx.Panel(self.splitter)
		
		# Panel for main content (right side)
		self.content_panel = panel=wx.Panel(self.splitter)

		# Create TreeCtrl for file listing in the left panel
		tree_sizer = wx.BoxSizer(wx.VERTICAL)
		if 1:
			self.refresh_btn = wx.Button(self.tree_panel, label="Refresh")
			tree_sizer.Add(self.refresh_btn, 0, wx.EXPAND | wx.ALL, 10)
			self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)

		self.tree = wx.TreeCtrl(self.tree_panel)
		tree_sizer.Add(self.tree, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
		self.root = self.tree.AddRoot('Question Files')
		
		
		self.tree_panel.SetSizer(tree_sizer)

		# Dummy files for demonstration. You can load actual file names from your system.
		
		#files = ['questions1.json', 'questions2.json', 'questions3.json']
		files = [f for f in os.listdir(self.questions_dir) if f.endswith('.json')]
		for file in files:
			self.tree.AppendItem(self.root, file)
		self.tree.Expand(self.root)
		# Main content in the right panel
		vbox = wx.BoxSizer(wx.VERTICAL)
		if 1:
			self.input_text = wx.TextCtrl(self.content_panel, style=wx.TE_MULTILINE)
			
			
			
			self.log_list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
			self.log_list_ctrl.InsertColumn(0, "Log Level Questions") #, width=100)
			
			#self.log_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_log_item_selected)
			hbox = wx.BoxSizer(wx.HORIZONTAL)
			hbox.Add(self.input_text, proportion=2, flag=wx.ALL | wx.EXPAND, border=5)
			hbox.Add(self.log_list_ctrl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

		vbox.Add(hbox, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
		if 1:
			self.add_question_btn = wx.Button(panel, label="Add Question")
			AsyncBind(wx.EVT_BUTTON, self.on_add_question, self.add_question_btn)
			vbox.Add(self.add_question_btn, flag=wx.ALL | wx.CENTER, border=10)

		if 1:
			self.ask_btn = wx.Button(self.content_panel, label="Ask GPT-4")
			AsyncBind(wx.EVT_BUTTON, self.on_chat, self.ask_btn)
			vbox.Add(self.ask_btn, flag=wx.ALL|wx.CENTER, border=10)
		if 1:
			self.timer_output = wx.StaticText(panel, label="")
			vbox.Add(self.timer_output, flag=wx.ALL|wx.CENTER, border=10)
		
		
		
		self.output_text = wx.TextCtrl(self.content_panel, style=wx.TE_MULTILINE)
		vbox.Add(self.output_text, proportion=1, flag=wx.ALL|wx.EXPAND, border=10)
		
		self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_tree_item_activated)
		#self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_log_item_activated, id=self.log_item_id)
		self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_right_click)
		#self.log_list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_log_item_activated)
		#self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.list_ctrl)
		self.log_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnClick, )

		self.content_panel.SetSizer(vbox)

		# Initialize the splitter to show both panels
		self.splitter.SplitVertically(self.tree_panel, self.content_panel)
		self.splitter.SetMinimumPaneSize(200)  # Minimum size the user can reduce the panel to
		
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		main_sizer.Add(self.splitter, 1, wx.EXPAND)
		
		if 1:
			self.status_bar = self.CreateStatusBar(3)  # 2 fields: one for text, one for the gauge
			self.status_bar.SetStatusText("Status: Ready")
			if 1:
			
				self.progress_bar = wx.Gauge(self.status_bar, range=100, style=wx.GA_HORIZONTAL)
				self.status_bar.SetStatusWidths([-1, 150,20])  # -1 will autosize, 150 for the gauge width
				rect = self.status_bar.GetFieldRect(1)  # get the rectangle of the second field
				self.progress_bar.SetPosition((rect.x, rect.y))
				self.progress_bar.SetSize((rect.width, rect.height))
			if 1:
				self.elapsed_time_text = wx.StaticText(self.status_bar, label="0s")
				rect_time = self.status_bar.GetFieldRect(2)
				self.elapsed_time_text.SetPosition((rect_time.x, rect_time.y))
				self.elapsed_time_text.SetSize((rect.width, rect.height))		
				self.elapsed_seconds = 0				
				
			if 1:
				self.timer = wx.Timer(self)
				self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
				self.progress = 0
				
		
		self.SetSizer(main_sizer)
		self.Show()
		self.log_item_dict = {}
		
		self.load_questions_into_tree()
		self.disable_all()
		
	def on_refresh(self, event):
		# Repopulate tree when "Refresh" button is clicked
		self.load_questions_into_tree()
	
	def disable_all(self):
		self.add_question_btn.Disable()
		self.ask_btn.Disable()
		self.ask_btn.Disable()
		self.input_text.Disable()
		self.output_text.Disable()
		self.log_list_ctrl.Disable()
			

	def enable_all(self):
		self.add_question_btn.Enable()
		self.ask_btn.Enable()
		self.ask_btn.Enable()
		self.input_text.Enable()
		self.output_text.Enable()
		self.log_list_ctrl.Enable()
		
		
	def on_timer(self, event):
		self.progress += 10
		self.elapsed_seconds += 1
		self.update_progress(self.progress)
		self.update_elapsed_time(self.elapsed_seconds)
		
		if self.progress >= 1000:
			self.timer.Stop()
			self.on_api_call_complete()
	def update_progress(self, value):
		self.progress_bar.SetValue(value)

	def on_api_call_complete(self):
		self.status_bar.SetStatusText("Status: API Call Complete")
		self.ask_btn.Enable()
		self.input_text.Enable()
		self.output_text.Enable()
		self.log_list_ctrl.Enable()
		self.progress_bar.SetValue(0)
		
	def OnClick(self, event):
		#question=event.GetText()
		selected_index = event.GetIndex()
		#item=event.GetItem()
		#idata=item.GetData()
		idata=self.log_item_dict[selected_index]
		#self.input_text.SetValue(idata['question'])
		self.input_text.SetValue(idata['question'])
		self.output_text.SetValue(idata['answer'])
		
	def update_elapsed_time(self, seconds):
		self.elapsed_time_text.SetLabel(f"{seconds}s")
			
	def on_log_item_selected(self, event):
		# Handle the selection of a log level question in the list control
		selected_index = event.GetIndex()

	def add_answer_question_pair(self,question_file, question, answer, selection):
		# Load the question file
		assert isfile(question_file)
		if os.path.exists(question_file):
			with open(question_file, 'r', encoding='utf-8') as file:
				questions_data = json.load(file)


		# Search for the question by title in the loaded data
		#pp(questions_data)
		questions_data['log']=json_log=questions_data.get('log',[])
			
		if 1:
			# Create a new dictionary containing the question and answer
			pair = {"question": question, "answer": answer, "selection":selection}
			
			# Append the new dictionary to the "log" list
			json_log.append(pair)

			# Save the updated question file
			with open(question_file, 'w', encoding='utf-8') as file:
				json.dump(questions_data, file, ensure_ascii=False, indent=4)
			return


			
	async def on_add_question(self, event):
		# Prompt user for the new file name


		
		with wx.TextEntryDialog(self, "Enter the name for the new question file:", "Add Question File") as dialog:
			dialog.SetValue(".json")
			text_ctrl = [child for child in dialog.GetChildren() if isinstance(child, wx.TextCtrl)][0]
			
			# This will select everything before the ".json" extension
			text_ctrl.SetSelection(0, len(text_ctrl.GetValue()) - 5)
			
			if dialog.ShowModal() == wx.ID_OK:
				file_name = dialog.GetValue()
				#file_name = dialog.GetValue()
				new_question_file_path = os.path.join(self.questions_dir, file_name)
				
				# Check if the file already exists
				if os.path.exists(new_question_file_path):
					wx.MessageBox(f"The file '{file_name}' already exists. Please choose a different name.", "Warning", wx.OK | wx.ICON_WARNING)
					return
		
				if not file_name.endswith(".json"):
					file_name += ".json"
				with open(os.path.join(self.questions_dir, file_name), 'w', encoding='utf-8') as f:
					json.dump({"question": "", "answer": ""}, f, ensure_ascii=False)
				self.load_questions_into_tree()

	def show_context_menu(self, item):
		context_menu = wx.Menu()

		# Add "Delete" option
		delete_option = context_menu.Append(wx.ID_ANY, "Delete")
		self.Bind(wx.EVT_MENU, lambda e: self.on_delete(item), delete_option)

		self.tree.PopupMenu(context_menu)
		context_menu.Destroy()
	def load_data(self, filename):
		assert isfile(filename), filename
		with open(filename, "r") as f:
			return json.load(f)

	def save_data(self, filename, jdata):
		assert isfile(filename), filename
		with open(filename, "w") as f:
			json.dump(jdata, f)


	def on_delete(self, item):
		# Avoid deleting the root item
		pyd = self.tree.GetItemData(item)
		question_to_delete = self.tree.GetItemText(item)
		
		if item != self.root:
			self.tree.Delete(item)
			filename= pyd['filename']
			lid=pyd['log_id']
			jdata=self.load_data(filename)
			del jdata['log'][lid]
			self.save_data(filename, jdata)

	def on_delete_file(self, item):
		pyd = self.tree.GetItemData(item)
		filename = pyd['filename']
		assert isfile(filename), filename
		path_to_delete = filename
		
		dlg = wx.MessageDialog(None, f"Are you sure you want to delete {path_to_delete}?", 'Warning', wx.YES_NO | wx.ICON_WARNING)
		result = dlg.ShowModal()
		
		if result == wx.ID_YES:
			os.remove(path_to_delete)
			self.tree.Delete(item)
			
		dlg.Destroy()
	
	def on_right_click(self, event):
	
	
		item = event.GetItem()
		pyd = self.tree.GetItemData(item)
		if pyd['level'] == 'log':  # If an item is clicked
			self.show_context_menu(item)
		elif pyd['level'] == 'title':
		
			
			"""Show context menu on right-click."""
			self.popup_menu = wx.Menu()

			# Create "Rename" item and bind it to the renaming function
			rename_item = self.popup_menu.Append(wx.ID_ANY, "Rename")
			#self.Bind(wx.EVT_MENU, self.on_rename_item, rename_item)
			
			self.Bind(wx.EVT_MENU, self.on_rename_question_file, rename_item)
			
			delete_file_option = self.popup_menu.Append(wx.ID_ANY, "Delete File")
			self.Bind(wx.EVT_MENU, lambda e: self.on_delete_file(item), delete_file_option)

			item = self.tree.GetSelection()
			if item.IsOk():
				self.tree.PopupMenu(self.popup_menu)
			self.popup_menu.Destroy()

	def on_rename_question_file(self, event):
		selected_file = os.path.join(self.questions_dir, self.tree.GetItemText(self.tree.GetSelection()))
		if selected_file and os.path.exists(selected_file):
			with wx.TextEntryDialog(self, "Rename Question File:", "Rename", os.path.basename(selected_file)) as dialog:
				
				# Retrieve the TextCtrl widget and set the selection
				text_ctrl = [child for child in dialog.GetChildren() if isinstance(child, wx.TextCtrl)][0]
				if text_ctrl:
					text_ctrl.SetSelection(0, len(os.path.splitext(os.path.basename(selected_file))[0]))

				if dialog.ShowModal() == wx.ID_OK:
					new_filename = dialog.GetValue()
					try:
						os.rename(selected_file, os.path.join(self.questions_dir, new_filename))
						self.load_questions_into_tree()
					except Exception as e:
						wx.MessageBox(str(e), "Error", wx.OK | wx.ICON_ERROR)



	def on_rename_item(self, event):
		"""Rename selected file and refresh TreeCtrl."""
		# Get current selection
		item = self.tree.GetSelection()
		if not item.IsOk():
			return
		
		old_filename = self.tree.GetItemText(item)
		old_path = os.path.join(self.questions_dir, old_filename)

		# Open a simple dialog to input the new filename
		rename_dlg = wx.TextEntryDialog(self, "Enter new filename:", "Rename File", old_filename)
		if rename_dlg.ShowModal() == wx.ID_OK:
			new_filename = rename_dlg.GetValue()
			new_path = os.path.join(self.questions_dir, new_filename)

			# Rename the file
			try:
				os.rename(old_path, new_path)
				# Refresh the TreeCtrl to reflect changes
				self.load_questions_into_tree()
			except Exception as e:
				wx.MessageBox(f"Error renaming file: {e}", "Error", wx.OK | wx.ICON_ERROR)

		rename_dlg.Destroy()
				
	def load_questions_into_tree(self):
		# Clear the existing tree
		self.tree.DeleteAllItems()

		# Get a list of files in the questions directory
		files = [f for f in os.listdir(self.questions_dir) if f.endswith('.json')]

		# Sort the files by their creation time (newest first)
		files.sort(key=lambda f: os.path.getctime(os.path.join(self.questions_dir, f)), reverse=True)

		# Create the root of the tree
		root = self.tree.AddRoot("Questions")
		#pp(files)
		# Add each file as a child under the root
		for filename in sorted([join(self.questions_dir,f) for f in files], key=os.path.getctime):
			with open( filename, 'r', encoding='utf-8') as file:
				question_data = json.load(file)

			title_question = question_data["question"]
			title_answer = question_data["answer"]
			log_questions = question_data.get("log", [])
			
			# Add the title question as a parent item
			bn=basename(filename)
			title_item = self.tree.AppendItem(root, f"{bn}:{title_question[:20]}")
			self.tree.SetItemData(title_item,dict(filename=filename, level='title', question= title_question, answer=title_answer))
			# Add log questions as child items under the title question
			for lid,log_question in enumerate(log_questions):
				log_question_item = self.tree.AppendItem(title_item, log_question["question"][:20])
				self.tree.SetItemData(log_question_item, dict(log_id=lid,filename=filename,question=log_question["question"], answer=log_question["answer"], level='log'))


		# Expand the root to show the files
		self.tree.Expand(root)
	def populate_log(self, filename):
		self.log_list_ctrl.DeleteAllItems()
		with open( filename, 'r', encoding='utf-8') as file:
			question_data = json.load(file)
			log_questions = question_data.get("log", [])
			for log_question in log_questions:
				new_item = self.log_list_ctrl.InsertItem(self.log_list_ctrl.GetItemCount(), log_question["question"])
				#print(111, new_item)
				item=self.log_list_ctrl.GetItem(new_item)
				self.log_item_dict[new_item] = dict(filename=filename,question=log_question["question"], answer=log_question["answer"], level='log')
				item.SetData( new_item)

				# Set data for other columns if needed
				#self.log_list_ctrl.SetItem(new_item, 1, "Column 2 Text")
				#self.log_list_ctrl.SetItem(new_item, 2, "Column 3 Text")

				# Optionally, you can select the new item
				#self.log_list_ctrl.Select(new_item)
		self.log_list_ctrl.SetColumnWidth(0, wx.LIST_AUTOSIZE)
		
	def _load_questions_into_tree(self):
		self.tree.DeleteAllItems()
		root = self.tree.AddRoot("Questions Files")
		
		files = [f for f in os.listdir(self.questions_dir) if os.path.isfile(os.path.join(self.questions_dir, f)) and f.endswith('.json')]
		
		for file in files:
			self.tree.AppendItem(root, file)
		
		self.tree.Expand(root)

		
	def on_tree_item_activated(self, event):
		"""Handle the double-click event on a TreeCtrl item."""
		item = event.GetItem()
		#txt = join(self.questions_dir, self.tree.GetItemText(item))
		pyd = self.tree.GetItemData(item)
		level=pyd['level']
		if level=='title':
			filename=pyd['filename']
			#filename =txt.split(':')[0]
			# Check if the item is not the root item
			if item != self.root:
				try:
					with open(filename, 'r', encoding='utf-8') as file:
						data = json.load(file)
						question = data.get("question", "")
						answer = data.get("answer", "")
						self.input_text.SetValue(question)
						self.output_text.SetValue(answer)
						self.populate_log( filename)
						 
						self.enable_all()
				except Exception as e:
				
					print(str(e))
					wx.MessageBox(f"Failed to load file: {filename}\nError: {e}", "Error", wx.OK | wx.ICON_ERROR)
		elif level=='log':
			pp(pyd)
			filename=pyd['filename']
			print(filename)

			question = pyd.get("question", "")
			print(question)
			answer = pyd.get("answer", "")
			self.input_text.SetValue(question)
			self.output_text.SetValue(answer)
			self.enable_all()
			self.populate_log( filename)
			
		else:
			wx.MessageBox(f"Unsupported level: {level}", "Error", wx.OK | wx.ICON_ERROR)
	def on_log_item_activated(self, event):
		item = event.GetItem()
		if item and self.tree.GetItemParent(item) != self.tree.GetRootItem():
			selected_question = self.tree.GetItemText(item)
			answer = self.tree.GetPyData(item)
			if answer is not None:
				self.input_text.SetValue(selected_question)
				self.output_text.SetValue(answer)
				
	async def on_chat(self, event):
		if 1:
			self.ask_btn.Disable()

			self.input_text.Disable()
			self.output_text.Disable()
			self.log_list_ctrl.Disable()
			
			self.status_bar.SetStatusText("Status: Calling API...")
			self.progress_bar.SetValue(0)
			self.progress = 0

			# Start the timer to update the progress every 50 milliseconds
			self.timer.Start(1000)
		
		#wx.BeginBusyCursor()
		#question_content = self.input_text.GetValue()
		
		start, end = self.input_text.GetSelection()
		if start == end:  # Nothing is selected
			question_content = self.input_text.GetValue()
		else:  # Some text is selected
			question_content = self.input_text.GetRange(start, end)
			
		response = await self.chat(question_content)
		self.output_text.SetValue(response)
		sel=self.tree.GetSelection()
		#print(222, sel)
		#print(self.tree.GetItemText(sel))
		# Save the response to the question file
		fn= self.tree.GetItemData(sel)['filename']
		#selected_file = os.path.join(self.questions_dir, self.tree.GetItemText(self.tree.GetSelection()))
		selected_file =  fn
		
		#print(selected_file)

		if os.path.exists(selected_file):
			with open(selected_file, 'r', encoding='utf-8') as f:
				data = json.load(f)
			
			# Use the current content of the TextCtrl for the question
			data['question'] = question_content
			data['answer'] = response
			data['selection'] = [start, end]
			
			with open(selected_file, 'w', encoding='utf-8') as f:
				json.dump(data, f, ensure_ascii=False, indent=4)
			self.add_answer_question_pair(selected_file,question_content, response, selection)
		#wx.EndBusyCursor()
		self.timer.Stop()
		self.on_api_call_complete()
		
	@timer_decorator
	async def chat(self, content):
		url = "https://api.openai.com/v1/chat/completions"
		headers = {
			"Authorization": f"Bearer {openai.api_key}",
			"Content-Type": "application/json"
		}
		data = {
			"model": "gpt-4",
			"messages": [{"role": "user", "content": content}]
		}

		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				if response.status == 200:
					resp_json = await response.json()
					return resp_json["choices"][0]["message"]["content"]
				else:
					return f"Error: {await response.text()}"

if __name__ == "__main__":
	app = WxAsyncApp()
	frame = MyFrame()
	app.SetTopWindow(frame)
	loop = asyncio.get_event_loop()
	loop.run_until_complete(app.MainLoop())
