from translations import TRANSLATIONS

class translationManager:
    def __init__(self, language='lt'):
        self.language = language

    def set_language(self, lang_code):
        self.language = lang_code

    def t(self, key, *args):
        text = TRANSLATIONS.get(self.language, {}).get(key, key)
        return text.format(*args) if args else text
