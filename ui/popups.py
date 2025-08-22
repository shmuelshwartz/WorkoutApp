# Popup dialog classes moved from main.py
from __future__ import annotations

from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

from ui.dialogs import FullScreenDialog
from ui.dialogs.add_metric_popup import METRIC_FIELD_ORDER
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import MDList
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider

import string
import re
import sqlite3

from core import DEFAULT_DB_PATH
from backend import metrics


