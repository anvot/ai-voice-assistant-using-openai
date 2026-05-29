import base64
import config
import httpx
import json
import openai
import random



http_client = httpx.Client(proxies=config.proxies)
openai_client = openai.OpenAI(api_key=config.api_key, http_client=http_client)
assistant = openai_client.beta.assistants.retrieve(config.assistant)


# Getting a response from the assistant when using function calls
class RequiresActionFromTools:

    def on_event(self, thread, on_event, outputs_of_plugins):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if on_event.event == 'thread.run.requires_action':
            #print("\nOUTPUT:", output)
            run_id = on_event.data.id  # Retrieve the run ID from the event data
            return self.handle_requires_action(thread, on_event.data, run_id, outputs_of_plugins)

    def handle_requires_action(self, thread, data, run_id, outputs_of_plugins):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            #print("\nTOOL:", tool, type(tool))
            if tool.function.name in outputs_of_plugins:
                tool_outputs.append({"tool_call_id": tool.id, "output": str(outputs_of_plugins[tool.function.name])})
            else:
                tool_outputs.append({"tool_call_id": tool.id, "output": "There is no data on the function being called. Try using your knowledge to answer the query."})

        # Submit all tool_outputs at the same time
        #print("\nOUTPUT:", tool_outputs)
        return self.submit_tool_outputs(thread, tool_outputs, run_id)

    def submit_tool_outputs(self, thread, tool_outputs, run_id):
        # Use the submit_tool_outputs_stream helper
        return openai_client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=thread.id,
            run_id=run_id,
            tool_outputs=tool_outputs,
        )


# Selecting a model temperature to diversify responses
def random_temperature():
    temperature = round(random.uniform(1.9, 2.0), 2)
    print(temperature)


def show_json(obj):
    show_json = json.loads(obj.model_dump_json())
    return show_json


def transcribe_audio(audio_file):
    global openai_client
    #audio_file = open("audio.wav", "rb")
    transcript = openai_client.audio.transcriptions.create(
        model=config.transcription_model,
        file=audio_file,
        prompt=config.prompt_for_transcribe  # Не работает с whisper-1
    )
    return transcript.text


# Model's response. Not an assistant's. For a quick response.
def fetch_ai_response_0(input_text):
    global openai_client
    messages = [{"role": "user", "content": input_text},
                {"role": "developer", "content": config.prompt_for_model
                 }]
    response = openai_client.chat.completions.create(
        model=config.model_name,
        temperature=random_temperature(),
        messages=messages,
        service_tier="priority",
        stream=True,
    )
    return response


# Assistant's response
def fetch_ai_response(thread, input_text):
    run = create_thread_and_run(thread, input_text)
    return run


def text_to_audio(text):
    global openai_client
    response = openai_client.audio.speech.create(
        model=config.tts_model,
        voice=config.voice,
        input=text,
        response_format=config.audio_response_format,
        speed=config.speech_speed
    )
    base64_audio = base64.b64encode(response.read()).decode("utf-8")
    return f'data:audio/wav;base64,{base64_audio}'


def text_to_audio_0(text):
    global openai_client
    response = openai_client.audio.speech.create(
        model=config.tts_model,
        voice=config.voice,
        input=text,
        response_format=config.audio_response_format,
        speed=config.speech_speed
    )
    base64_audio = base64.b64encode(response.read()).decode("utf-8")
    return f'data:audio/wav;base64,{base64_audio}'


def submit_message(assistant_id, thread, user_message):
    global openai_client
    openai_client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_message
    )
    submit_message = openai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
        stream=True
    )
    return submit_message


def create_thread_and_run(thread, user_input):
    run = submit_message(assistant.id, thread, user_input)
    return run


def cancel_run(thread, run_id):
    global openai_client
    openai_client.beta.threads.runs.cancel(
        thread_id=thread.id,
        run_id=run_id
    )


def messages_list(thread):
    global openai_client
    messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
    return show_json(messages)


# Assistant response function in stream mode
def assistants_response(event):
    assistants_response = show_json(event)['data']['delta']['content'][0]['text']['value']
    return assistants_response


# Assistant response function when calling functions in stream mode
def assistants_call_function_response(event):
    assistants_call_function_response = show_json(event)['data']['delta']['step_details']['tool_calls'][0]['function']['arguments']
    return assistants_call_function_response


def assistants_run_id(event):
    assistants_run_id = show_json(event)['data']['id']
    return assistants_run_id

'''
def dialog_messages_history(dialog_messages):
    messages = []
    for dialog_message in dialog_messages:
        messages.append({"role": "user", "content": dialog_message["client"]})
        messages.append({"role": "assistant", "content": dialog_message["assistant"]})
    return messages
'''

# Since the dialogue history loaded into the assistant is limited to 32 elements, we bypass this limitation by loading the dialogue as a single line
def dialog_messages_history(dialog_messages):
    messages = "Below is the text of your conversation with the user. Study this text to learn the history of the conversation: "
    for dialog_message in dialog_messages:
        messages += ("{" + f"user: {dialog_message["client"]}" +
                     "}, " + "{" + f"assistant: {dialog_message["assistant"]}" +
                     "}, "
                     )
    return [{"role": "user", "content": messages}]


def assistants_run_status(event):
    assistants_run_status = show_json(event)['data']['status']
    return assistants_run_status
