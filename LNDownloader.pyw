import Tkinter

class LNDownloader(Tkinter.Tk):

    def __init__(self, *args, **kwargs):

        Tkinter.Tk.__init__(self, *args, **kwargs)
        self.initialize_window_properties(self)

        root_frame = self.create_root_frame(self)
        self.populate_with_ui_elements(root_frame)

        root_frame.tkraise()

    def initialize_window_properties(self, root_window):

        root_window.title('LawNet Downloader')
        root_window.geometry('321x74')

    def create_root_frame(self, root_window):
        
        root_frame = Tkinter.Frame(self)
        root_frame.pack(side='top', fill='none', expand = False)
        root_frame.grid_rowconfigure(0, weight=1)
        root_frame.columnconfigure(0, weight=1)

        return root_frame

    def populate_with_ui_elements(self, parent_container):

        uid_label = Tkinter.Label(parent_container, text='Username:', font=('Verdana', 12))
        uid_label.grid(row=0, column=0, sticky='e')
        uid_entry = Tkinter.Entry(parent_container)
        uid_entry.grid(row=0, column=1, sticky='w')

        pw_label = Tkinter.Label(parent_container, text='Password:', font=('Verdana', 12))
        pw_label.grid(row=1, column=0, sticky='e')
        pw_entry = Tkinter.Entry(parent_container, show="*")
        pw_entry.grid(row=1, column=1, sticky='w')

        def show_popup_dialog():

            popup = Tkinter.Toplevel()
            popup_label_text = "username is {0}\npassword is {1}".format(uid_entry.get(), pw_entry.get())
            popup_label = Tkinter.Label(popup, text=popup_label_text)
            popup_label.pack()

        go_button = Tkinter.Button(parent_container, text='Go!', width=8, command=show_popup_dialog)
        go_button.grid(row=2, column=0, columnspan=2)

app = LNDownloader()
app.mainloop()
