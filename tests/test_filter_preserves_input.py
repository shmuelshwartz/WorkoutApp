from tests.test_metric_input_tabs import MetricInputScreen

class DummyList:
    def __init__(self):
        self.children = []
    def add_widget(self, widget):
        self.children.append(widget)
    def clear_widgets(self):
        self.children.clear()

def test_filter_toggle_preserves_input():
    screen = MetricInputScreen()
    screen.metrics_list = DummyList()

    class DummySession:
        def __init__(self):
            self.exercises = [{
                "name": "Bench",
                "sets": 1,
                "metric_defs": [
                    {"name": "Weight", "type": "int", "is_required": True, "input_timing": "post_set"},
                    {"name": "Comment", "type": "str", "is_required": False, "input_timing": "post_set"},
                ],
                "results": [],
            }]
            self.pending_pre_set_metrics = {}
            self.awaiting_post_set_metrics = False
            self.current_exercise = 0
            self.current_set = 0
            self.current_set_start_time = 0
            self.last_set_time = 0
    screen.session = DummySession()
    screen.update_metrics()

    weight_row = next(r for r in screen.metrics_list.children if r.metric_name == "Weight")
    weight_row.input_widget.text = "123"

    screen.toggle_filter("additional")

    weight_row = next(r for r in screen.metrics_list.children if r.metric_name == "Weight")
    assert getattr(weight_row.input_widget, "text", "") == "123"
