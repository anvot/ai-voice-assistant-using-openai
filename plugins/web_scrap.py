import requests
import config
import database
from bs4 import BeautifulSoup
from readability import Document
from .plugin import Plugin

class WebPageReaderPlugin(Plugin):
    """
    A plugin to read and return the main text content of a given web page URL using the Readability library.
    """
    def get_source_name(self) -> str:
        return "WebPageReader"

    def get_spec(self) -> [dict]:
        return [{
            "name": "read_web_page",
            "description": "Reads the main text content of a web page given its URL using Readability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the web page to read."
                    }
                },
                "required": ["url"],
            },
        }]

    async def execute(self, model, function_name, helper, **kwargs) -> dict:
        url = kwargs.get('url')
        context_window = config.models["info"][model]["context_window"]
        #context_window = config.context_window
        #print(context_window)
        if not url:
            return {"error": "URL parameter is required"}

        try:
            response = requests.get(url)
            if response.status_code == 200:
                doc = Document(response.text)
                content_html = doc.summary()
                # Используем BeautifulSoup для дополнительной очистки и получения текста
                soup = BeautifulSoup(content_html, 'html.parser')
                main_text = soup.get_text()

                #print(context_window, '      ', len(main_text[:context_window]))
                #return {"content": main_text[:context_window]}
                return [main_text[:context_window]]
            else:
                return {"error": f"Failed to retrieve the web page. Status code: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}