"""Minimal KivyMD text editor used for manual testing."""

from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
import os

KV = '''
BoxLayout:
    orientation: 'vertical'

    MDTopAppBar:
        title: "TXT File Editor"
        elevation: 10
        left_action_items: [["folder", lambda x: app.file_manager_open()]]

    ScrollView:
        MDTextField:
            id: editor
            hint_text: "Open a .txt file to edit"
            size_hint_y: None
            height: self.minimum_height
            multiline: True
            font_size: "18sp"
            padding: [10, 10, 10, 10]

    MDRaisedButton:
        text: "Save"
        size_hint: None, None
        size: "120dp", "40dp"
        pos_hint: {"center_x": 0.5}
        on_release: app.save_file()
'''

class TxtEditorApp(MDApp):
    """Simple text editor implemented with KivyMD widgets."""

    def __init__(self, **kwargs):
        """Initialise widgets used by the demo application."""
        super().__init__(**kwargs)
        self.file_manager = None
        self.current_file = None
        self.dialog = None

    def build(self):
        """Create the interface and file manager."""
        self.theme_cls.primary_palette = "Blue"
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path,
            preview=False,
        )
        return Builder.load_string(KV)

    def file_manager_open(self):
        """Open the file manager starting from the user's documents folder."""
        start_path = os.path.expanduser("~/Documents")
        if not os.path.exists(start_path):
            start_path = os.path.expanduser("~")
        self.file_manager.show(start_path)
        self.file_manager.search = "all"  # or use: self.file_manager.ext = [".txt"]

    def select_path(self, path):
        """Handle selection of a file from the file manager."""
        self.exit_manager()
        if path.endswith(".txt"):
            self.current_file = path
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.root.ids.editor.text = f.read()
                toast(f"Opened: {os.path.basename(path)}")
            except Exception as e:
                self.show_error_dialog(f"Error reading file:\n{e}")
        else:
            self.show_error_dialog("Please select a .txt file.")

    def exit_manager(self, *args):
        """Close the file manager widget."""
        self.file_manager.close()

    def save_file(self):
        """Write the current editor contents back to disk."""
        if not self.current_file:
            self.show_error_dialog("No file loaded to save.")
            return
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.root.ids.editor.text)
            toast(f"Saved to: {os.path.basename(self.current_file)}")
        except Exception as e:
            self.show_error_dialog(f"Error saving file:\n{e}")

    def show_error_dialog(self, message):
        """Display a simple dialog with an error message."""
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title="Error",
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK", on_release=lambda x: self.dialog.dismiss()
                )
            ],
        )
        self.dialog.open()

if __name__ == "__main__":
    TxtEditorApp().run()
