#!/usr/bin/python
# -*- coding: latin-1 -*-

import hashlib, wx, os, Queue, threading
from wx.lib.wordwrap import wordwrap
import  wx.lib.filebrowsebutton as filebrowse

""" 
TODO: 
1. Better Tutorial.
2. Preview pane for images. #wx.fold panel bar + demo image browser?
3. Ablity to delete specific listing after selecting.
4. Export lists to a file
5. Move Browse options in File menu?
7. Make every listing selectable - use grid instead of list?
8. Make listing headers do something on click - re-list listngs ascending, descending, etc.
"""

#-----------------------------Globals-----------------------------------------

img_sha_h = {} #stores: hash_of_file, path_of_file
global unique_pathnames
unique_pathnames = img_sha_h.viewvalues()

duplicate_img_sha_h = {} #stores: path_of_duplicate_file, path_of_file from img_sha_h
global duplicate_pathnames
duplicate_pathnames = duplicate_img_sha_h.viewvalues()

queue = Queue.Queue() #global queue that everything can access

# Allows for on-change signals for the unique files detected.
class UniquePathnames(object):
    def __init__(self):
        self._unique_pathnames = img_sha_h.viewvalues()
        self._observers = []

    def get_pathnames(self):
        return self._unique_pathnames

    def set_pathnames(self, value):
        self._unique_pathnames = value
        for callback in self._observers:
            callback(self._unique_pathnames)

    unique_pathnames = property(get_pathnames, set_pathnames)

    def bind_to(self, callback):
        self._observers.append(callback)

# Allows for on-change signals for the duplicate files detected.
class DuplicatePathnames(object):
    def __init__(self):
        self._duplicate_pathnames = duplicate_img_sha_h.viewvalues()
        self._observers = []

    def get_pathnames(self):
        return self._duplicate_pathnames

    def set_pathnames(self, value):
        self._duplicate_pathnames = value
        for callback in self._observers:
            callback(self._duplicate_pathnames)

    duplicate_pathnames = property(get_pathnames, set_pathnames)

    def bind_to(self, callback):
        self._observers.append(callback)

uniques_data = UniquePathnames()
duplicates_data = DuplicatePathnames()

# File hashing and hash storage function.
class ThreadHash(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            #grabs pathname from queue
            path_name = self.queue.get()

            temp_hash = (hashlib.sha1(file(path_name, 'rb').read()).hexdigest())
            if temp_hash in img_sha_h and img_sha_h[temp_hash] != path_name:
                #We want reverse storing logic for multiple duplicates. 
                #eg, B and C are dupes of A, but we want to keep track of both B and C and not store by Hash value.

                #use str(...) at storage time. Not sure if the best idea. Strings are more malleable than unicode though.
                duplicate_img_sha_h[str(path_name)] = img_sha_h[str(temp_hash)]
            else:
                img_sha_h[str(temp_hash)] = str(path_name)

            #signals to queue job is done
            self.queue.task_done()

# controls the multi-threaded aspect of hashing files.
def ProcessFiles(self, filenames):
    # spawn a pool of threads, and pass them queue instance 
    for i in range(3):
        t = ThreadHash(queue)
        t.setDaemon(True)
        t.start()

    # populate queue with data   
    for path_name in filenames:
        if os.path.isdir(path_name):
            for r,d,f in os.walk(path_name):
                for files in f:
                    queue.put(os.path.join(r,files))
        else:
            queue.put(path_name)

    # wait on the queue until everything has been processed     
    queue.join()
            
    # update the pathname global vars
    uniques_data.unique_pathnames = img_sha_h.viewvalues()
    duplicates_data.duplicate_pathnames = duplicate_img_sha_h.viewvalues()

# Drag and Drop functionality; triggers processing too.
class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        self.window.SetInsertionPointEnd()
        self.window.WriteText("\nLoaded...\n")

        for path_name in filenames:
            self.window.WriteText(path_name + '\n')

        ProcessFiles(self, filenames)

#-----------------------------Panels------------------------------------------

# File loading history and drag-n-drop panel.
class FileDropPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, -1, "\nFiles Loaded:"), 0, wx.EXPAND|wx.ALL, 2)

        self.text = wx.TextCtrl(self, -1, "", style = wx.TE_MULTILINE|wx.HSCROLL|wx.TE_READONLY)

        DropTarget = MyFileDropTarget(self)
        self.text.SetDropTarget(DropTarget)
        sizer.Add(self.text, 1, wx.EXPAND)

        buttonBox = wx.BoxSizer(wx.VERTICAL)

        self.fbb = filebrowse.FileBrowseButton(
            self, -1, size=(300, -1), changeCallback = self.fbbCallback, labelText="Select a file:"
        )
        self.dbb = filebrowse.DirBrowseButton(
            self, -1, size=(300, -1), changeCallback = self.dbbCallback, labelText="Select a folder:"
        )

        buttonBox.Add(self.fbb, 1, wx.ALIGN_CENTER_VERTICAL)
        buttonBox.Add(self.dbb, 1, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(buttonBox, 0)
        self.SetSizer(sizer)

        self.WriteText("Drag and drop files and folders here to load them.\n")

    def WriteText(self, text):
        self.text.WriteText(text)

    def SetInsertionPointEnd(self):
        self.text.SetInsertionPointEnd()

    def Clear(self):
        self.text.Clear()

    def fbbCallback(self, evt):
        ProcessFiles(self, [evt.GetString()])
        self.text.WriteText("\nLoaded...")
        self.text.WriteText('\n' + evt.GetString() + '\n')

    def dbbCallback(self, evt):
        ProcessFiles(self, [evt.GetString()])
        self.text.WriteText("\nLoaded...")
        self.text.WriteText('\n' + evt.GetString() + '\n')

# Unique files panel; unique files will be listed here when loaded.
class UniquesPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, -1, "\nUniques Files Loaded:"), 0, wx.EXPAND|wx.ALL, 2)

        self.list=wx.ListCtrl(self, -1,style=wx.LC_REPORT|wx.LC_EDIT_LABELS|wx.LC_NO_HEADER|wx.LC_SORT_ASCENDING)
        self.list.Show(True)
        self.list.InsertColumn(0,"Uniques", width=817)

        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.data = uniques_data
        self.data.bind_to(self.Update)

    def WriteText(self, col1):
        self.list.InsertStringItem(0,col1)

    def Update(self, duplicate_pathnames):
        self.list.DeleteAllItems()
        for k in img_sha_h:
            self.WriteText(str(img_sha_h[k]))
        self.Stripe()

    def Stripe(self):
        if self.list.GetItemCount()>0:
            for x in range(self.list.GetItemCount()):
                if x % 2==0:
                    self.list.SetItemBackgroundColour(x,wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT))
                else:
                    self.list.SetItemBackgroundColour(x,wx.WHITE)

# Duplicate files panel; duplicate files will be listed here in pairs with their originally loaded counterparts.
class DuplicatesPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.list=wx.ListCtrl(self, -1,style=wx.LC_REPORT|wx.LC_EDIT_LABELS|wx.LC_SORT_ASCENDING|wx.LC_HRULES|wx.LC_VRULES)
        self.list.Show(True)
        self.list.InsertColumn(0,"Duplicate Files found:", width=412)
        self.list.InsertColumn(1,"Original/Unique versions:", width=405)

        sizer.Add(self.list, 1, wx.EXPAND)

        self.data = duplicates_data
        self.data.bind_to(self.Update)

        buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        ID_DeleteBtn      = wx.NewId()
        ID_ResetBtn       = wx.NewId()
        buttonBox.Add(wx.Button(self, ID_ResetBtn, 'Reset Files Loaded'), 0)
        buttonBox.Add(wx.Button(self, ID_DeleteBtn, 'Delete All Duplicate Files Found'), 0)

        sizer.Add(buttonBox, 0, wx.ALIGN_RIGHT)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_BUTTON, self.Delete, id=ID_DeleteBtn)
        self.Bind(wx.EVT_BUTTON, self.ResetAll, id=ID_ResetBtn)

    def WriteText(self, col1, col2):
        currRow = self.list.InsertStringItem(0,col1)
        self.list.SetStringItem(currRow,1,col2)

    def Update(self, duplicate_pathnames):
        self.list.DeleteAllItems()
        for (key, value) in duplicate_img_sha_h.iteritems():
            self.WriteText(str(key), str(value))
        self.Stripe()

    def Stripe(self):
        if self.list.GetItemCount()>0:
            for x in range(self.list.GetItemCount()):
                if x % 2==1:
                    self.list.SetItemBackgroundColour(x,wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT))
                else:
                    self.list.SetItemBackgroundColour(x,wx.WHITE)

    # Delete Duplicates button.
    def Delete(self, e):
        dlg = wx.MessageDialog(self, "Are you sure you wish to delete all of the the detected file duplicates?", "Deletion Confirmation", wx.YES_NO | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            for key in duplicate_img_sha_h.viewkeys():
                os.remove(key)
            img_sha_h.clear()
            duplicate_img_sha_h.clear()
            uniques_data.unique_pathnames = img_sha_h.viewvalues()
            duplicates_data.duplicate_pathnames = duplicate_img_sha_h.viewvalues()
            self.WriteText("-Empty-", "")
        dlg.Destroy()

    # Reset file listings button.
    def ResetAll(self, e):
        img_sha_h.clear()
        duplicate_img_sha_h.clear()
        uniques_data.unique_pathnames = img_sha_h.viewvalues()
        duplicates_data.duplicate_pathnames = duplicate_img_sha_h.viewvalues()

class FrrFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title,  pos=(200,200), size=(1280,720)) # Assuming everyone uses a 720p+ resolution.

        # font
        self.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.NORMAL, False))

        # menus
        filemenu = wx.Menu()
        helpmenu = wx.Menu()

        # file Menu
        menuExit = filemenu.Append(wx.ID_EXIT, "&Exit"," Exit/Close the IRR Utility")

        # help menu
        menuAbout = helpmenu.Append(wx.ID_ABOUT, "&About", "Information about the IRR Utility")
        menuTutorial = helpmenu.Append(wx.ID_HELP, "&Quick Tutorial", "Tutorial and Help Information")

        # menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&File") # Adding the "filemenu" to the MenuBar
        menuBar.Append(helpmenu, "&Help") # Adding the "help" to the MenuBar

        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # set menu events
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnTutorial, menuTutorial)
        
        # layout
        self.SetAutoLayout(True)
        all_box = wx.BoxSizer(wx.HORIZONTAL)
        all_box.Add(wx.StaticLine(self, -1), 0, wx.EXPAND)
        right_box = wx.BoxSizer(wx.VERTICAL)
        
        right_box.Add(UniquesPanel(self), 1, wx.EXPAND)
        right_box.Add(DuplicatesPanel(self), 1, wx.EXPAND)

        all_box.Add(FileDropPanel(self), 1, wx.EXPAND)
        all_box.Add(right_box, 2, wx.EXPAND)
        
        self.SetSizer(all_box)
        self.Show(True)

    def OnAbout(self, e):
        info = wx.AboutDialogInfo()
        info.Name = "File Redundancy Reducer"
        info.Version = "1.0"
        info.Copyright = "(C) 2013 Tyler Wood"
        info.Description = wordwrap(
            "File Redundancy Reducer (FRR) is a program used to help reduce the number of redundantly saved files on a computer."
            
            "\n\nIn general, there is a time consuming problem with downloading files from the internet: downloaded files are not easily "
            "distinguishable by their default filenames or thumbnails, so they are often manually categorized and organized. "
            "\n\nFRR is a tool which helps make this process easier by listing which files have been saved redundantly and "
            "can be discarded safely. The main benefit for doing this is to help save hard drive space and time of users "
            "who are tired of manually sorting through images and deleting duplicates.\n\n", 
            350, wx.ClientDC(self))

        info.WebSite = ("https://github.com/zelus-craft/File-Redundancy-Reducer", "Source Available on Github")
        wx.AboutBox(info)

    def OnExit(self, e):
        self.Close(True)  # Close the program.

    def OnTutorial(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog(
            self, 
            "1. Drag and Drop files/folders into the left pane to load them. Selecting files/folders through the Browse option works too."
            "\n\n2. The right panes will automatically update with the loaded files, listing which loaded files are unique and which are duplicates."
            "\n\n3. Click the 'Delete All Duplicate Files Found' button to delete the duplicates listed."
            "\n\n4. Click the 'Reset Files Loaded' button to reset the detected unique and duplicate files, which resets the program.",
            "Quick Tutorial",
            wx.OK)
        dlg.ShowModal() # Show the tutorial.
        dlg.Destroy() # Destroy the tutorial when closed.

app = wx.App(False)
frame = FrrFrame(None, 'File Redundancy Reducer')
app.MainLoop()