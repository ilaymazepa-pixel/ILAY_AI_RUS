import os
import re
import json
import threading
import urllib.request
import urllib.parse

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


APP_NAME = "ILAY AI 6.0"

BLACK = (0.039, 0.039, 0.051, 1)
DARK = (0.070, 0.070, 0.090, 1)
DARK2 = (0.110, 0.110, 0.137, 1)
GREEN = (0.31, 1, 0.55, 1)
WHITE = (0.92, 0.92, 0.94, 1)
GRAY = (0.56, 0.56, 0.61, 1)
BLUE = (0.22, 0.39, 0.71, 1)
YELLOW = (0.94, 0.82, 0.31, 1)

memory_file = "ilay_memory.json"


def safe_read_memory():
    data = {
        "name": "Игрок",
        "messages": 0,
        "facts": []
    }

    if not os.path.exists(memory_file):
        return data

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict):
            data["name"] = str(
                loaded.get("name", "Игрок")
            )

            try:
                data["messages"] = int(
                    loaded.get("messages", 0)
                )
            except Exception:
                data["messages"] = 0

            facts = loaded.get("facts", [])

            if isinstance(facts, list):
                data["facts"] = [
                    str(x) for x in facts
                ]

    except Exception:
        pass

    return data


def safe_write_memory(data):
    try:
        with open(
            memory_file,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception:
        pass


def clean_html(text):
    text = re.sub(
        r"<.*?>",
        "",
        text
    )

    return (
        text
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#x27;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .strip()
    )


def internet_get(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
            "Mozilla/5.0 ILAY-AI/6.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=10
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def search_internet(query):
    encoded = urllib.parse.quote_plus(query)

    url = (
        "https://html.duckduckgo.com/html/?q="
        + encoded
    )

    html = internet_get(url)

    titles = re.findall(
        r'class="result__a"[^>]*>(.*?)</a>',
        html,
        re.S
    )

    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</',
        html,
        re.S
    )

    titles = [
        clean_html(x)
        for x in titles
    ]

    snippets = [
        clean_html(x)
        for x in snippets
    ]

    results = []

    for i in range(
        min(5, len(titles))
    ):
        snippet = ""

        if i < len(snippets):
            snippet = snippets[i]

        results.append(
            (
                titles[i],
                snippet
            )
        )

    return results


def search_wikipedia(query):
    encoded = urllib.parse.quote(query)

    url = (
        "https://ru.wikipedia.org/w/api.php?"
        "action=query&"
        "list=search&"
        "srsearch="
        + encoded
        + "&format=json&"
        "utf8=1&"
        "srlimit=4"
    )

    data = internet_get(url)

    obj = json.loads(data)

    results = obj.get(
        "query",
        {}
    ).get(
        "search",
        []
    )

    output = []

    for item in results:
        title = item.get(
            "title",
            ""
        )

        snippet = clean_html(
            item.get(
                "snippet",
                ""
            )
        )

        if title:
            output.append(
                (
                    title,
                    snippet
                )
            )

    return output


def calculate(expression):
    expression = re.sub(
        r"[^0-9+\-*/().% ]",
        "",
        expression
    )

    if not expression:
        return None

    try:
        result = eval(
            expression,
            {
                "__builtins__": {}
            },
            {}
        )

        if isinstance(
            result,
            (int, float)
        ):
            return result

    except Exception:
        pass

    return None


class MessageLabel(Label):

    def __init__(
        self,
        text="",
        color=WHITE,
        **kwargs
    ):
        super().__init__(
            text=text,
            **kwargs
        )

        self.color = color
        self.font_size = sp(17)
        self.halign = "left"
        self.valign = "top"
        self.text_size = (
            Window.width - dp(45),
            None
        )

        self.size_hint_y = None

        self.padding = (
            dp(5),
            dp(5)
        )

        self.bind(
            width=self.update_text_size
        )

        self.bind(
            texture_size=self.update_height
        )

    def update_text_size(
        self,
        *args
    ):
        self.text_size = (
            max(
                dp(100),
                self.width - dp(10)
            ),
            None
        )

    def update_height(
        self,
        *args
    ):
        self.height = (
            self.texture_size[1]
            + dp(12)
        )


class ChatMessage(BoxLayout):

    def __init__(
        self,
        who,
        text,
        **kwargs
    ):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=(
                dp(10),
                dp(4)
            ),
            spacing=dp(2),
            **kwargs
        )

        if who == "ILAY":
            color = GREEN
            prefix = "ILAY"
        else:
            color = WHITE
            prefix = "YOU"

        name = Label(
            text=prefix,
            color=color,
            font_size=sp(14),
            bold=True,
            size_hint_y=None,
            height=dp(24),
            halign="left",
            valign="middle"
        )

        name.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        body = MessageLabel(
            text=text,
            color=WHITE,
        )

        self.add_widget(name)
        self.add_widget(body)

        Clock.schedule_once(
            self.update_height,
            0
        )

    def update_height(
        self,
        *args
    ):
        self.height = (
            sum(
                child.height
                for child in self.children
            )
            + dp(12)
        )


class ILAYApp(App):

    def build(self):

        self.title = APP_NAME

        self.memory = safe_read_memory()

        self.internet_busy = False

        self.root_layout = BoxLayout(
            orientation="vertical"
        )

        with self.root_layout.canvas.before:
            Color(*BLACK)
            self.background = RoundedRectangle(
                pos=self.root_layout.pos,
                size=self.root_layout.size,
                radius=[0]
            )

        self.root_layout.bind(
            pos=self.update_background,
            size=self.update_background
        )

        self.create_header()

        self.scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(7),
            scroll_type=[
                "bars",
                "content"
            ],
            scroll_distance=dp(10),
            size_hint_y=1
        )

        self.chat = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(5),
            padding=(
                dp(8),
                dp(12)
            )
        )

        self.chat.bind(
            minimum_height=self.chat.setter(
                "height"
            )
        )

        self.scroll.add_widget(
            self.chat
        )

        self.root_layout.add_widget(
            self.scroll
        )

        self.create_input()

        self.add_message(
            "ILAY",
            "Я снова здесь, "
            + self.memory["name"]
            + ". 🧠"
        )

        self.add_message(
            "ILAY",
            "ILAY AI 6.0 запущен. "
            "Мобильный режим активен."
        )

        return self.root_layout

    def update_background(
        self,
        *args
    ):
        self.background.pos = (
            self.root_layout.pos
        )

        self.background.size = (
            self.root_layout.size
        )

    def create_header(self):

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(70),
            padding=(
                dp(15),
                dp(5)
            )
        )

        title = Label(
            text="ILAY AI 6.0",
            color=GREEN,
            font_size=sp(26),
            bold=True,
            halign="left",
            valign="middle"
        )

        title.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        self.status = Label(
            text="● ONLINE",
            color=GREEN,
            font_size=sp(14),
            halign="right",
            valign="middle"
        )

        self.status.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        header.add_widget(title)

        header.add_widget(
            self.status
        )

        self.root_layout.add_widget(
            header
        )

    def create_input(self):

        panel = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(105),
            padding=(
                dp(10),
                dp(10)
            ),
            spacing=dp(8)
        )

        self.input = TextInput(
            hint_text="Напиши сообщение...",
            multiline=True,
            font_size=sp(17),
            foreground_color=WHITE,
            hint_text_color=GRAY,
            background_color=DARK2,
            cursor_color=GREEN,
            padding=(
                dp(12),
                dp(12)
            ),
            size_hint_x=0.78
        )

        self.input.bind(
            on_text_validate=self.on_enter
        )

        send = Button(
            text="SEND",
            font_size=sp(17),
            bold=True,
            color=WHITE,
            background_normal="",
            background_color=BLUE,
            size_hint_x=0.22
        )

        send.bind(
            on_release=self.send_message
        )

        panel.add_widget(
            self.input
        )

        panel.add_widget(send)

        self.root_layout.add_widget(
            panel
        )

    def on_enter(
        self,
        instance
    ):
        self.send_message()

    def add_message(
        self,
        who,
        text
    ):
        message = ChatMessage(
            who,
            text
        )

        self.chat.add_widget(
            message
        )

        Clock.schedule_once(
            self.scroll_to_bottom,
            0.05
        )

    def scroll_to_bottom(
        self,
        *args
    ):
        self.scroll.scroll_y = 0

    def save(self):
        safe_write_memory(
            self.memory
        )

    def memory_text(self):

        result = (
            "🧠 ПАМЯТЬ ILAY\n\n"
            "Имя: "
            + self.memory["name"]
            + "\n"
            "Сообщений: "
            + str(
                self.memory["messages"]
            )
        )

        facts = self.memory["facts"]

        if facts:

            result += "\n\nФакты:\n"

            for fact in facts:
                result += (
                    "• "
                    + fact
                    + "\n"
                )

        return result

    def local_answer(
        self,
        text
    ):

        t = text.lower().strip()

        if t == "память":
            return self.memory_text()

        if "что ты помнишь" in t:
            return self.memory_text()

        if t.startswith(
            "меня зовут "
        ):

            name = text[
                len("меня зовут "):
            ].strip()

            if name:

                self.memory["name"] = name

                self.save()

                return (
                    "Запомнил. Тебя зовут "
                    + name
                    + ". 🧠"
                )

        if t.startswith(
            "запомни "
        ):

            fact = text[
                len("запомни "):
            ].strip()

            if fact:

                self.memory["facts"].append(
                    fact
                )

                self.save()

                return (
                    "Запомнил: "
                    + fact
                    + " 🧠"
                )

        if (
            "сколько будет" in t
            or t.startswith("посчитай ")
            or t.startswith("математика ")
        ):

            expression = t

            expression = expression.replace(
                "сколько будет",
                ""
            )

            expression = expression.replace(
                "посчитай",
                ""
            )

            expression = expression.replace(
                "математика",
                ""
            )

            result = calculate(
                expression
            )

            if result is not None:
                return (
                    "🧮 Ответ: "
                    + str(result)
                )

        if t == "привет":

            return (
                "Привет, "
                + self.memory["name"]
                + "! 😎"
            )

        if "соник" in t:
            return (
                "СОНИК! 🦔💨 "
                "Скорость на максимум!"
            )

        if "марио" in t:
            return (
                "Марио! 🍄 "
                "Где-то рядом должна "
                "быть зелёная труба."
            )

        if "кинито" in t:
            return (
                "KinitoPET... 👀 "
                "Интересный компьютерный персонаж."
            )

        if "кто ты" in t:
            return (
                "Я ILAY AI 6.0 🤖\n\n"
                "У меня есть память, "
                "поиск в интернете, "
                "математика и мобильный интерфейс."
            )

        if "что ты умеешь" in t:
            return (
                "Я умею:\n"
                "• общаться\n"
                "• запоминать факты\n"
                "• считать\n"
                "• искать информацию в интернете\n"
                "• работать на телефоне"
            )

        return None

    def send_message(
        self,
        *args
    ):

        text = self.input.text.strip()

        if not text:
            return

        self.input.text = ""

        self.add_message(
            "Ты",
            text
        )

        self.memory["messages"] += 1

        response = self.local_answer(
            text
        )

        if response is not None:

            self.add_message(
                "ILAY",
                response
            )

        else:

            self.add_message(
                "ILAY",
                "🌐 Ищу информацию..."
            )

            self.status.text = (
                "● SEARCHING"
            )

            self.status.color = YELLOW

            self.internet_busy = True

            thread = threading.Thread(
                target=self.internet_worker,
                args=(text,),
                daemon=True
            )

            thread.start()

        self.save()

    def internet_worker(
        self,
        query
    ):

        try:

            web = search_internet(
                query
            )

            try:
                wiki = search_wikipedia(
                    query
                )
            except Exception:
                wiki = []

            result = ""

            if wiki:

                result += (
                    "📚 ВИКИПЕДИЯ\n\n"
                )

                for title, snippet in wiki:

                    result += (
                        "• "
                        + title
                        + "\n"
                    )

                    if snippet:
                        result += (
                            snippet
                            + "\n"
                        )

                    result += "\n"

            if web:

                result += (
                    "🌐 ИНТЕРНЕТ\n\n"
                )

                for i, (
                    title,
                    snippet
                ) in enumerate(web):

                    result += (
                        str(i + 1)
                        + ". "
                        + title
                        + "\n"
                    )

                    if snippet:
                        result += (
                            snippet
                            + "\n"
                        )

                    result += "\n"

            if not result:

                result = (
                    "Я ничего подходящего "
                    "не нашёл."
                )

            Clock.schedule_once(
                lambda dt: self.finish_search(
                    result
                )
            )

        except Exception as error:

            result = (
                "⚠️ Ошибка интернета:\n"
                + str(error)
            )

            Clock.schedule_once(
                lambda dt: self.finish_search(
                    result
                )
            )

    def finish_search(
        self,
        result
    ):

        self.internet_busy = False

        self.status.text = "● ONLINE"
        self.status.color = GREEN

        self.add_message(
            "ILAY",
            result
        )

        self.save()


class ILAYAppWrapper(ILAYApp):
    pass


if __name__ == "__main__":
    ILAYAppWrapper().run()