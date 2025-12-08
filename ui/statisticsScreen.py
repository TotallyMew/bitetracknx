from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import Screen
from kivy.app import App 
from database.database import Database
from TranslationManager import translationManager

db = Database()

class StatisticsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translator = translationManager('lt')

    def set_language(self, language):
        lang_code = 'lt' if language == 'Lithuanian' else 'en'
        self.translator.set_language(lang_code)

        # 🌀 Update Spinner values
        self.ids.spinner.values = [
            self.translator.t("filter_all"),
            self.translator.t("filter_day"),
            self.translator.t("filter_week"),
            self.translator.t("filter_month")
        ]

        # Preserve current selection if possible
        current_selection = self.ids.spinner.text
        if current_selection not in self.ids.spinner.values:
            self.ids.spinner.text = self.translator.t("filter_all")

        # 🆙 Update back button
        if "back_button" in self.ids:
            self.ids.back_button.text = self.translator.t("go_back")




    def on_enter(self):
        current_language = App.get_running_app().language
        self.set_language(current_language)
        self.set_filter('Visi')



    def load_statistics_data(self, filter_type):
        stats_list = self.ids.stats_list
        stats_list.clear_widgets()

        try:
            if filter_type == 'Visi':
                products = db.get_all_products()
            elif filter_type == 'Diena':
                products = db.get_products_today()
            elif filter_type == 'Savaitė':
                products = db.get_products_this_week()
            elif filter_type == 'Mėnuo':
                products = db.get_products_this_month()
            else:
                products = []

            if products is None:
                stats_list.add_widget(Label(
                    text=self.translator.t("no_data"),
                    size_hint_y=None,
                    height=40
                ))
                return

            for product in products:
                row = BoxLayout(size_hint_y=None, height=40, spacing=10)

                product_button = Button(
                    text=product['product_name'],
                    on_press=lambda btn, p=product: self.edit_product(p)
                )

                delete_button = Button(
                    text=self.translator.t("delete"),
                    size_hint_x=None,
                    width=100,
                    on_press=lambda btn, p_id=product['id']: self.confirm_delete_popup(p_id)
                )

                row.add_widget(product_button)
                row.add_widget(delete_button)
                stats_list.add_widget(row)

        except Exception as e:
            self.show_error("Nepavyko užkrauti duomenų. Bandykite dar kartą.")
            print(f"Klaida įkeliant statistiką: {e}")

    def show_error(self, message):
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        label = Label(text=message)
        ok_button = Button(text="OK", size_hint_y=None, height=40)

        popup = Popup(title="Klaida", content=content, size_hint=(0.7, 0.3), auto_dismiss=False)
        ok_button.bind(on_release=popup.dismiss)

        content.add_widget(label)
        content.add_widget(ok_button)
        popup.open()

    def confirm_delete_popup(self, product_id):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        label = Label(text="Ar tikrai norite ištrinti šį produktą?")

        button_row = BoxLayout(spacing=10, size_hint_y=None, height=40)
        yes_button = Button(text=self.translator.t("confirm"))
        no_button = Button(text=self.translator.t("cancel"))

        popup = Popup(title=self.translator.t("confirm"), content=content, size_hint=(0.7, 0.4), auto_dismiss=False)

        yes_button.bind(on_release=lambda x: self._delete_and_close(product_id, popup))
        no_button.bind(on_release=lambda x: popup.dismiss())

        button_row.add_widget(yes_button)
        button_row.add_widget(no_button)

        content.add_widget(label)
        content.add_widget(button_row)

        popup.open()

    def show_confirmation(self, message):
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        label = Label(text=message)
        ok_button = Button(text="OK", size_hint_y=None, height=40)

        popup = Popup(title="Informacija", content=content, size_hint=(0.6, 0.3), auto_dismiss=False)

        ok_button.bind(on_release=popup.dismiss)
        content.add_widget(label)
        content.add_widget(ok_button)

        popup.open()

    def _delete_and_close(self, product_id, popup):
        db.delete_product(product_id)
        popup.dismiss()
        self.set_filter(self.ids.spinner.text)
        self.show_confirmation(self.translator.t("deleted"))

    def edit_product(self, product):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        name_input = TextInput(text=product['product_name'])

        def save_changes(_):
            new_name = name_input.text.strip()

            if not new_name:
                self.show_error("Pavadinimas negali būti tuščias.")
                return

            if len(new_name) > 255:
                self.show_error("Pavadinimas negali viršyti 255 simbolių.")
                return

            db.update_product(product['id'], new_name)
            self.set_filter(self.ids.spinner.text)
            popup.dismiss()
            self.show_confirmation(self.translator.t("edited"))

        def cancel(_):
            popup.dismiss()

        save_btn = Button(text=self.translator.t("update"), size_hint_y=None, height=40)
        save_btn.bind(on_release=save_changes)

        cancel_btn = Button(text=self.translator.t("cancel"), size_hint_y=None, height=40)
        cancel_btn.bind(on_release=cancel)

        content.add_widget(name_input)
        content.add_widget(save_btn)
        content.add_widget(cancel_btn)

        popup = Popup(title=self.translator.t("edit_product"), content=content, size_hint=(0.8, 0.5))
        popup.open()

    def set_filter(self, value):
        # Reverse map the translated text to internal keywords
        key_map = {
            self.translator.t("filter_all"): "Visi",
            self.translator.t("filter_day"): "Diena",
            self.translator.t("filter_week"): "Savaitė",
            self.translator.t("filter_month"): "Mėnuo"
        }

        internal_value = key_map.get(value, "Visi")
        self.load_statistics_data(internal_value)


    def go_back(self):
        self.manager.current = "main"
