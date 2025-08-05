from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button


class PreviousWorkoutsScreen(Screen):
    """Screen displaying a 2D scrollable comparison of exercise sessions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Hardcoded test data
        sessions = [
            {
                "name": "Push Day - Aug 5",
                "sets": [
                    {"reps": "5 reps", "weight": "80kg", "tempo": "2-1-1"},
                    {"reps": "5 reps", "weight": "82kg", "tempo": "2-1-1"},
                    {"reps": "5 reps", "weight": "82kg", "tempo": "2-1-1"},
                ],
            },
            {
                "name": "Push Day - Aug 2",
                "sets": [
                    {"reps": "4 reps", "weight": "78kg", "tempo": "3-1-1"},
                    {"reps": "5 reps", "weight": "80kg", "tempo": "2-0-1"},
                    {"reps": "5 reps", "weight": "81kg", "tempo": "2-0-1"},
                ],
            },
            {
                "name": "Push Day - Jul 30",
                "sets": [
                    {"reps": "6 reps", "weight": "75kg", "tempo": "2-2-1"},
                    {"reps": "5 reps", "weight": "77kg", "tempo": "2-1-2"},
                    {"reps": "5 reps", "weight": "78kg", "tempo": "2-1-2"},
                ],
            },
        ]

        root = BoxLayout(orientation="vertical")

        # Top row: session headers
        header_row = BoxLayout(size_hint_y=None, height=40)
        header_row.add_widget(Label(text="Metric", size_hint_x=None, width=100))
        self.header_scroll = ScrollView(do_scroll_y=False)
        header_grid = GridLayout(rows=1, size_hint_x=None, height=40)
        header_grid.bind(minimum_width=header_grid.setter("width"))
        for idx, session in enumerate(sessions):
            lbl = Label(
                text=f"[b]{session['name']}[/b]",
                markup=True,
                size_hint_x=None,
                width=150,
                halign="center",
                valign="middle",
            )
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            header_grid.add_widget(lbl)
        self.header_scroll.add_widget(header_grid)
        header_row.add_widget(self.header_scroll)
        root.add_widget(header_row)

        # Body: vertical scroll for sets and metrics
        body_scroll = ScrollView(do_scroll_x=False)
        body_layout = BoxLayout(orientation="horizontal", size_hint_y=None)
        body_layout.bind(minimum_height=body_layout.setter("height"))

        # Left column with set/metric labels
        label_grid = GridLayout(cols=1, size_hint_x=None, width=100, size_hint_y=None)
        label_grid.bind(minimum_height=label_grid.setter("height"))
        num_sets = len(sessions[0]["sets"])
        for i in range(1, num_sets + 1):
            label_grid.add_widget(Label(text=f"Set {i}", size_hint_y=None, height=30))
            for metric in ("Reps", "Weight", "Tempo"):
                label_grid.add_widget(
                    Label(text=f"  - {metric}", size_hint_y=None, height=30)
                )
        body_layout.add_widget(label_grid)

        # Right area with session data
        self.data_scroll = ScrollView(do_scroll_y=False)
        data_grid = GridLayout(cols=len(sessions), size_hint=(None, None))
        data_grid.bind(minimum_width=data_grid.setter("width"))
        data_grid.bind(minimum_height=data_grid.setter("height"))

        for session in sessions:
            col = GridLayout(cols=1, size_hint_y=None)
            col.bind(minimum_height=col.setter("height"))
            for set_data in session["sets"]:
                col.add_widget(Label(text="", size_hint_y=None, height=30))
                col.add_widget(Label(text=set_data["reps"], size_hint_y=None, height=30))
                col.add_widget(Label(text=set_data["weight"], size_hint_y=None, height=30))
                col.add_widget(Label(text=set_data["tempo"], size_hint_y=None, height=30))
            data_grid.add_widget(col)

        self.data_scroll.add_widget(data_grid)
        body_layout.add_widget(self.data_scroll)
        body_scroll.add_widget(body_layout)
        root.add_widget(body_scroll)

        # Back button to return to rest screen
        back_btn = Button(
            text="Back to Rest",
            size_hint_y=None,
            height=40,
            on_release=lambda *_: App.get_running_app().root.__setattr__(
                "current", "rest"
            ),
        )
        root.add_widget(back_btn)

        # Sync horizontal scrolling between headers and data
        def sync_header_scroll(instance, value):
            self.header_scroll.scroll_x = value

        def sync_data_scroll(instance, value):
            self.data_scroll.scroll_x = value

        self.data_scroll.bind(scroll_x=sync_header_scroll)
        self.header_scroll.bind(scroll_x=sync_data_scroll)

        self.add_widget(root)
