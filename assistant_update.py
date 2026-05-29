import httpx
import config
import openai


http_client = httpx.Client(proxies=config.proxies)
client = openai.OpenAI(api_key=config.api_key, http_client=http_client)


assistant_update = client.beta.assistants.update(
    config.assistant,
    instructions=config.prompt_for_assistant,
    name=config.assistant_name,
    tools=config.tools,
    model=config.assistants_model,
    metadata={},
    top_p=config.top_p,
    temperature=config.temperature,
    response_format=config.assistant_response_format,
)

#tools=[{"type": "file_search"}]

print(assistant_update)