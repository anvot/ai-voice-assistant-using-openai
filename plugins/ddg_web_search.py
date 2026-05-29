from itertools import islice
import os
from typing import Dict

from duckduckgo_search import DDGS



def web_search(**kwargs) -> Dict:
    try:
        safesearch = os.getenv('DUCKDUCKGO_SAFESEARCH', 'moderate')
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(
                kwargs['query'],
                region=kwargs.get('region', 'wt-wt'),
                safesearch=safesearch
            )
            results = list(islice(ddgs_gen, 3))

            if results is None or len(results) == 0:
                return {"Result": "No good DuckDuckGo Search Result was found"}

            def to_metadata(result: Dict) -> Dict[str, str]:
                return {
                    "snippet": result["body"],
                    "title": result["title"],
                    "link": result["href"],
                }
            #print({"result": [to_metadata(result) for result in results]})
            return {"result": [to_metadata(result) for result in results]}
    except Exception as e:
        print(f"\n ERROR: {e}")
        return {"web_search": "По какой-то причине не удалось получить данные на запрос. Попробуйте позже."}

web_search_json = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Execute a web search for the given query and return a list of results",
        "strict": True,
        "parameters": {
            "type": "object",
            "required": [
                "plugin",
                "query",
                "region"
            ],
            "properties": {
                "plugin": {
                    "type": "string",
                    "description": "name of the plugin is 'web_search'"
                },
                "query": {
                    "type": "string",
                    "description": "The user query"
                },
                "region": {
                    "type": "string",
                    "enum": [
                        "xa-ar",
                        "xa-en",
                        "ar-es",
                        "au-en",
                        "at-de",
                        "be-fr",
                        "be-nl",
                        "br-pt",
                        "bg-bg",
                        "ca-en",
                        "ca-fr",
                        "ct-ca",
                        "cl-es",
                        "cn-zh",
                        "co-es",
                        "hr-hr",
                        "cz-cs",
                        "dk-da",
                        "ee-et",
                        "fi-fi",
                        "fr-fr",
                        "de-de",
                        "gr-el",
                        "hk-tzh",
                        "hu-hu",
                        "in-en",
                        "id-id",
                        "id-en",
                        "ie-en",
                        "il-he",
                        "it-it",
                        "jp-jp",
                        "kr-kr",
                        "lv-lv",
                        "lt-lt",
                        "xl-es",
                        "my-ms",
                        "my-en",
                        "mx-es",
                        "nl-nl",
                        "nz-en",
                        "no-no",
                        "pe-es",
                        "ph-en",
                        "ph-tl",
                        "pl-pl",
                        "pt-pt",
                        "ro-ro",
                        "ru-ru",
                        "sg-en",
                        "sk-sk",
                        "sl-sl",
                        "za-en",
                        "es-es",
                        "se-sv",
                        "ch-de",
                        "ch-fr",
                        "ch-it",
                        "tw-tzh",
                        "th-th",
                        "tr-tr",
                        "ua-uk",
                        "uk-en",
                        "us-en",
                        "ue-es",
                        "ve-es",
                        "vn-vi",
                        "wt-wt"
                    ],
                    "description": "The region to use for the search. Infer this from the language used for the query. Default to `wt-wt` if not specified"
                }
            },
            "additionalProperties": False
        }
    }
}
