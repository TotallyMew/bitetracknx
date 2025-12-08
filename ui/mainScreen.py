from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

from ui.statisticsScreen import StatisticsScreen
from database.database import Database
from LLM import send_query
from voiceToText import VoiceToText
from kivy.clock import Clock

from TranslationManager import translationManager

PRODUCTS = []
db = Database()
Builder.load_file("UI.kv")


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.voice_to_text = VoiceToText()
        self.translator = translationManager('lt')  # Default language

    def start_recording(self):
        if not self.voice_to_text.is_recording:
            self.ids.record_button.text = self.translator.t("stop_recording")
            self.ids.transcription.text = self.translator.t("start_recording")
            self.voice_to_text.start_recording(self.handle_transcription_result)
        else:
            self.ids.record_button.text = self.translator.t("start_recording")
            self.ids.transcription.text = self.translator.t("stop_recording")
            self.voice_to_text.is_recording = False


    def handle_transcription_result(self, result):
        def update(dt):
            self.ids.transcription.text = result
            if "Klaida" not in result:
                self.send_to_llm()
        Clock.schedule_once(update)

    def set_language(self, language):
        self.voice_to_text.set_language(language)
        lang_code = 'lt' if language == 'Lithuanian' else 'en'
        self.translator.set_language(lang_code)

        App.get_running_app().language = language  # Store globally

        self.ids.transcription.text = self.translator.t('language_changed', language)

        for btn_id, key in {
            "save_button": "save",
            "cancel_button": "cancel",
            "delete_button": "delete",
            "confirm_button": "confirm",
            "reports_button": "reports",
            "record_button": "start_recording",
            "apply_changes_button": "apply_changes",
            "recognized_label": "recognized_products"
        }.items():
            if btn_id in self.ids:
                self.ids[btn_id].text = self.translator.t(key)

        # Send language to statistics screen too
        self.manager.get_screen("statistics").set_language(language)




    def clear_text(self):
        self.ids.transcription.text = ""

    def send_to_llm(self):
        query = self.ids.transcription.text
        self.clear_text()
        result = send_query(query)
        self.display_results(result)

    def display_results(self, result):
        self.ids.transcription.text = result
        self.save_to_products(result)
        self.update_product_list()

    def save_to_products(self, result):
        PRODUCTS.clear()
        lines = result.split("\n")
        for idx, line in enumerate(lines, 1):
            if line.strip().startswith("- Patiekalas:"):
                name = line.split(":", 1)[1].strip()
                PRODUCTS.append({"id": idx, "product_name": name})

    def save_to_database(self):
        if not PRODUCTS:
            return
        for product in PRODUCTS:
            db.add_product(product["product_name"])
        self.ids.transcription.text = ""
        PRODUCTS.clear()
        self.update_product_list()

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        layout.add_widget(Label(text=self.translator.t("product_saved")))
        ok_btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(ok_btn)
        popup = Popup(title="OK", content=layout, size_hint=(0.6, 0.3))
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def update_product_list(self):
        product_list = self.ids.product_list
        product_list.clear_widgets()
        for product in PRODUCTS:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

            edit_btn = Button(
                text=product["product_name"],
                size_hint_y=None,
                height=40,
                on_press=lambda btn, pid=product["id"]: self.edit_product(pid)
            )
            del_btn = Button(
                text=self.translator.t("delete"),
                size_hint_x=None,
                width=100,
                height=40,
                on_press=lambda btn, pid=product["id"]: self.confirm_delete(pid)
            )
            row.add_widget(edit_btn)
            row.add_widget(del_btn)
            product_list.add_widget(row)

    def edit_product(self, product_id):
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            return

        self.product_input = TextInput(
            text=product["product_name"],
            size_hint_y=None,
            height=40
        )

        save_button = Button(
            text=self.translator.t("save"),
            size_hint_y=None,
            height=40
        )
        cancel_button = Button(
            text=self.translator.t("cancel"),
            size_hint_y=None,
            height=40
        )

        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_layout.add_widget(self.product_input)

        buttons_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(cancel_button)
        popup_layout.add_widget(buttons_layout)

        popup = Popup(
            title=self.translator.t("edit_product"),
            content=popup_layout,
            size_hint=(0.5, 0.4)
        )

        save_button.bind(on_press=lambda btn: self.save_edited_product(product_id, popup))
        cancel_button.bind(on_press=popup.dismiss)
        popup.open()


    def save_edited_product(self, product_id, popup):
        new_name = self.product_input.text.strip()
        if new_name is None:
            self.show_error("Pavadinimas negali būti tuščias.")
            return
        if len(new_name) > 255:
            self.show_error("Pavadinimas negali viršyti 255 simbolių.")
            return
        for product in PRODUCTS:
            if product["id"] == product_id:
                product["product_name"] = new_name
        popup.dismiss()
        self.update_product_list()

    def confirm_delete(self, product_id):
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        name = product["product_name"]

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        layout.add_widget(Label(text=f"Ar tikrai norite ištrinti {name}?"))

        btns = BoxLayout(spacing=10, size_hint_y=None, height=40)
        confirm_btn = Button(text=self.translator.t("confirm"))
        cancel_btn = Button(text=self.translator.t("cancel"))
        btns.add_widget(confirm_btn)
        btns.add_widget(cancel_btn)

        layout.add_widget(btns)

        popup = Popup(title=self.translator.t("confirm"), content=layout, size_hint=(0.6, 0.4))
        confirm_btn.bind(on_press=lambda btn: self.delete_product(product_id, name, popup))
        cancel_btn.bind(on_press=lambda btn: popup.dismiss())
        popup.open()

    def delete_product(self, product_id, name, popup):
        popup.dismiss()
        global PRODUCTS
        PRODUCTS = [p for p in PRODUCTS if p["id"] != product_id]
        self.update_product_list()

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        layout.add_widget(Label(text=f"{self.translator.t('product_deleted')} '{name}'"))
        ok_btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(ok_btn)

        popup = Popup(title="OK", content=layout, size_hint=(0.6, 0.3))
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def update_from_text(self):
        global PRODUCTS
        PRODUCTS.clear()
        self.ids.product_list.clear_widgets()
        lines = self.ids.transcription.text.strip().split("\n")
        id_counter = 1
        for line in lines:
            if line.strip().startswith("- Patiekalas:"):
                name = line.split(":", 1)[1].strip()
                PRODUCTS.append({"id": id_counter, "product_name": name})
                id_counter += 1
        self.update_product_list()

    def show_error(self, message):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        layout.add_widget(Label(text=message))
        ok_btn = Button(text="OK", size_hint_y=None, height=40)
        layout.add_widget(ok_btn)
        popup = Popup(title="Klaida", content=layout, size_hint=(0.7, 0.3))
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def load_statistics(self):
        self.manager.current = "statistics"


class MyApp(App):
    def build(self):
        self.db = db
        self.language = "Lithuanian"  # Store selected language globally
        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(StatisticsScreen(name="statistics"))
        return sm


if __name__ == "__main__":
    MyApp().run()
