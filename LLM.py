from typing import Dict, List, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput

from ui.statisticsScreen import StatisticsScreen
from database.database import Database
from LLM import send_query
from voiceToText import VoiceToText
from TranslationManager import translationManager


PRODUCTS: List[Dict[str, str]] = []
db = Database()

Builder.load_file("UI.kv")


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voice_to_text = VoiceToText()
        self.translator = translationManager("lt")  # default language
        self.product_input: Optional[TextInput] = None

    # ------------------------------------------------------------------ #
    # Voice recording & transcription
    # ------------------------------------------------------------------ #

    def start_recording(self) -> None:
        if not self.voice_to_text.is_recording:
            self._set_recording_ui_state(recording=True)
            self.voice_to_text.start_recording(self.handle_transcription_result)
        else:
            self._set_recording_ui_state(recording=False)
            self.voice_to_text.stop_recording()

    def _set_recording_ui_state(self, recording: bool) -> None:
        key = "stop_recording" if recording else "start_recording"
        self.ids.record_button.text = self.translator.t(key)
        self.ids.transcription.text = self.translator.t(key)
        self.voice_to_text.is_recording = recording

    def handle_transcription_result(self, result: str) -> None:
        def update_ui(_dt: float) -> None:
            self.ids.transcription.text = result
            if "Klaida" not in result:
                self.send_to_llm()

        Clock.schedule_once(update_ui)

    # ------------------------------------------------------------------ #
    # Internationalization
    # ------------------------------------------------------------------ #

    def set_language(self, language: str) -> None:
        """Orchestruoja kalbos pakeitimą (SRP + mažesnis coupling)."""
        self._update_voice_language(language)
        self._update_translation_language(language)
        self._store_global_language(language)
        self._update_transcription_message(language)
        self._update_widget_labels()
        self._notify_statistics_screen(language)

    def _update_voice_language(self, language: str) -> None:
        self.voice_to_text.set_language(language)

    def _update_translation_language(self, language: str) -> None:
        lang_code = "lt" if language == "Lithuanian" else "en"
        self.translator.set_language(lang_code)

    @staticmethod
    def _store_global_language(language: str) -> None:
        app = App.get_running_app()
        if app is not None:
            app.language = language

    def _update_transcription_message(self, language: str) -> None:
        self.ids.transcription.text = self.translator.t("language_changed", language)

    def _update_widget_labels(self) -> None:
        mapping = {
            "save_button": "save",
            "cancel_button": "cancel",
            "delete_button": "delete",
            "confirm_button": "confirm",
            "reports_button": "reports",
            "record_button": "start_recording",
            "apply_changes_button": "apply_changes",
            "recognized_label": "recognized_products",
        }

        for widget_id, key in mapping.items():
            widget = self.ids.get(widget_id)
            if widget is not None:
                widget.text = self.translator.t(key)

    def _notify_statistics_screen(self, language: str) -> None:
        statistics_screen = self.manager.get_screen("statistics")
        if hasattr(statistics_screen, "set_language"):
            statistics_screen.set_language(language)

    # ------------------------------------------------------------------ #
    # LLM integration
    # ------------------------------------------------------------------ #

    def clear_text(self) -> None:
        self.ids.transcription.text = ""

    def send_to_llm(self) -> None:
        query = self.ids.transcription.text
        self.clear_text()
        result = send_query(query)
        self.display_results(result)

    def display_results(self, result: str) -> None:
        self.ids.transcription.text = result
        self.save_to_products(result)
        self.update_product_list()

    # ------------------------------------------------------------------ #
    # Products in memory
    # ------------------------------------------------------------------ #

    def save_to_products(self, result: str) -> None:
        PRODUCTS.clear()
        for index, line in enumerate(result.splitlines(), start=1):
            if not line.strip().startswith("- Patiekalas:"):
                continue
            name = line.split(":", 1)[1].strip()
            PRODUCTS.append({"id": index, "product_name": name})

    def save_to_database(self) -> None:
        if not PRODUCTS:
            return

        self._persist_products()
        self._clear_products_state()
        self._show_save_success_popup()

    def _persist_products(self) -> None:
        for product in PRODUCTS:
            db.add_product(product["product_name"])

    def _clear_products_state(self) -> None:
        self.ids.transcription.text = ""
        PRODUCTS.clear()
        self.update_product_list()

    def _show_save_success_popup(self) -> None:
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        layout.add_widget(Label(text=self.translator.t("product_saved")))

        ok_btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(ok_btn)

        popup = Popup(title="OK", content=layout, size_hint=(0.6, 0.3))
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def update_product_list(self) -> None:
        product_list = self.ids.product_list
        product_list.clear_widgets()

        for product in PRODUCTS:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)

            edit_btn = Button(
                text=product["product_name"],
                size_hint_y=None,
                height=40,
            )
            edit_btn.bind(
                on_press=lambda _btn, pid=product["id"]: self.edit_product(pid)
            )

            del_btn = Button(
                text=self.translator.t("delete"),
                size_hint_x=None,
                width=100,
                height=40,
            )
            del_btn.bind(
                on_press=lambda _btn, pid=product["id"]: self.confirm_delete(pid)
            )

            row.add_widget(edit_btn)
            row.add_widget(del_btn)
            product_list.add_widget(row)

    def edit_product(self, product_id: int) -> None:
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            return

        self.product_input = TextInput(
            text=product["product_name"],
            size_hint_y=None,
            height=40,
        )

        save_button = Button(
            text=self.translator.t("save"),
            size_hint_y=None,
            height=40,
        )
        cancel_button = Button(
            text=self.translator.t("cancel"),
            size_hint_y=None,
            height=40,
        )

        popup_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        popup_layout.add_widget(self.product_input)

        buttons_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(cancel_button)
        popup_layout.add_widget(buttons_layout)

        popup = Popup(
            title=self.translator.t("edit_product"),
            content=popup_layout,
            size_hint=(0.5, 0.4),
        )

        save_button.bind(
            on_press=lambda _btn: self.save_edited_product(product_id, popup)
        )
        cancel_button.bind(on_press=popup.dismiss)
        popup.open()

    def save_edited_product(self, product_id: int, popup: Popup) -> None:
        new_name = (self.product_input.text or "").strip()
        if not new_name:
            self.show_error("Pavadinimas negali būti tuščias.")
            return
        if len(new_name) > 255:
            self.show_error("Pavadinimas negali viršyti 255 simbolių.")
            return

        for product in PRODUCTS:
            if product["id"] == product_id:
                product["product_name"] = new_name
                break

        popup.dismiss()
        self.update_product_list()

    def confirm_delete(self, product_id: int) -> None:
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            return

        name = product["product_name"]
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        layout.add_widget(Label(text=f"Ar tikrai norite ištrinti {name}?"))

        btns = BoxLayout(spacing=10, size_hint_y=None, height=40)
        confirm_btn = Button(text=self.translator.t("confirm"))
        cancel_btn = Button(text=self.translator.t("cancel"))
        btns.add_widget(confirm_btn)
        btns.add_widget(cancel_btn)

        layout.add_widget(btns)

        popup = Popup(
            title=self.translator.t("confirm"),
            content=layout,
            size_hint=(0.6, 0.4),
        )
        confirm_btn.bind(
            on_press=lambda _btn: self.delete_product(product_id, name, popup)
        )
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def delete_product(self, product_id: int, name: str, popup: Popup) -> None:
        popup.dismiss()
        global PRODUCTS
        PRODUCTS = [p for p in PRODUCTS if p["id"] != product_id]
        self.update_product_list()

        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        layout.add_widget(
            Label(text=f"{self.translator.t('product_deleted')} '{name}'")
        )
        ok_btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(ok_btn)

        info_popup = Popup(
            title="OK",
            content=layout,
            size_hint=(0.6, 0.3),
        )
        ok_btn.bind(on_press=info_popup.dismiss)
        info_popup.open()

    def update_from_text(self) -> None:
        PRODUCTS.clear()
        self.ids.product_list.clear_widgets()

        id_counter = 1
        for line in self.ids.transcription.text.strip().splitlines():
            if not line.strip().startswith("- Patiekalas:"):
                continue
            name = line.split(":", 1)[1].strip()
            PRODUCTS.append({"id": id_counter, "product_name": name})
            id_counter += 1

        self.update_product_list()

    def show_error(self, message: str) -> None:
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)
        layout.add_widget(Label(text=message))
        ok_btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(ok_btn)
        popup = Popup(title="Klaida", content=layout, size_hint=(0.7, 0.3))
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def load_statistics(self) -> None:
        self.manager.current = "statistics"


class MyApp(App):
    def build(self):
        self.db = db
        self.language = "Lithuanian"
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(StatisticsScreen(name="statistics"))
        return sm


if __name__ == "__main__":
    MyApp().run()
