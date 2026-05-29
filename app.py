import base64
import cherrypy
import config
import database
from datetime import datetime
import errno
from flask import Flask, request, render_template, jsonify, Response, send_from_directory
from flask_httpauth import HTTPBasicAuth
from io import BytesIO
import logging
import openai_utilities
import queue
import random
import ssl
import threading
import time
from werkzeug.security import generate_password_hash, check_password_hash
import json
import re


db = database.Database()

# Current time generation function (for tracking delays)
def current_time():
    return time.strftime("%H:%M:%S", time.localtime()) + "." + str(time.time()).split(".")[1]

# Ignoring the error when streaming is interrupted
class WerkzeugFilter(logging.Filter):
    def filter(self, record):
        if "Error on request" in record.getMessage():
            return False
        return True

# Set up logging CherryPy
# cherrypy.log.screen = False  # Disable logging to the screen


error_logger = logging.getLogger("cherrypy.error")
access_logger = logging.getLogger("cherrypy.access")

# Hide some types of error messages
class IgnoreSSLError(logging.Filter):
    def filter(self, record):
        if "ssl.SSLEOFError" in str(record.msg):
            return False
        if "Broken pipe" in str(record.msg):  # Ignore'Broken pipe'
            return False
        if "Connection reset by peer" in str(record.msg):  # Ignore client connection reset
            return False
        return True


error_logger.addFilter(IgnoreSSLError())
logger = logging.getLogger('werkzeug')
logger.addFilter(WerkzeugFilter())

app = Flask(__name__)
auth = HTTPBasicAuth()

# Specified user credentials
users = {config.username_1: generate_password_hash(config.password_1),
         config.username_2: generate_password_hash(config.password_2)
         }
client_username = ""

openai_client = openai_utilities.openai_client
#thread = openai_client.beta.threads
#thread = ""
thread = openai_client.beta.threads.create()

# Transcribed text (global variables)
full_text = ' '
full_text_0 = ' '

# Elements of the queue data structure
audio_queue = queue.Queue()
sse_queue = queue.Queue()

# List of audio "plugs"
first_audio_file = []

# Event in the stream (for tracking items in the queue)
queue_empty = threading.Event()

# We set it at the beginning to indicate that the queue is empty.
queue_empty.set()

# List of punctuation marks for dividing text into fragments
punctuation_mark_list = ['.', ',', '!', '?', ':', ';', '...', '-']

# Triggers for stopping audio responses (global variables). To be able to interrupt the assistant
stop_play = False
stop_play_0 = False
finalize_event = threading.Event()  # global Event for thread termination finalize()
finalize_event_0 = threading.Event()  # global Event for thread termination finalize_0()

# Assistant response readiness trigger
assistants_response_ready = False

# Launch ID in the assistant
run_id = ''

# The time delay coefficient for the pronunciation of an audio fragment (different for different audio formats)
# t_koef = 0.00004 # для аудио формата "mp3"
t_koef = 0.00015 # для аудио формата "opus"


# A variable for numbering audio recordings. Used only for debugging.
n = 0

# Audio "plugs" to fill the response waiting period
def waitings_jingles():
    global first_audio_file
    for number in range(7):
        jingle = f"{config.waitings_jingles_path}" + str(number) + ".mp3"
        with open(jingle, 'rb') as jingle:
            jingle_bytes = jingle.read()
        base64_audio = base64.b64encode(jingle_bytes).decode("utf-8")
        first_audio_file.append(f'data:audio/wav;base64,{base64_audio}')

'''
# Speech audio "plugs" to fill the response waiting period
for_first_audio_response = ['I get it. This is what I think about it.',
                            'Okay. Let me think for a moment...',
                            'Okay. Just wait a few seconds. I'll figure it out.',
                            'Yeah, I get it. I'll try to formulate it now.',
                            'Soooo. You know... .Mmmmmmmmmmmmm. That's it.',
                            ]

for text in enumerate(for_first_audio_response):
    first_audio_file.append(openai_utilities.text_to_audio_0(text[1]))


'''

def register_client_if_not_exists(client):
    if not db.check_if_client_exists(client):
        db.add_new_client(
            client_username=client,
            first_name="",
            last_name=""
        )
        db.start_new_dialog(client)

    if db.get_client_attribute(client, "current_dialog_id") is None:
        db.start_new_dialog(client)


@auth.verify_password
def verify_password(username, password):
    global client_username
    if username in users and check_password_hash(users.get(username), password):
        client_username = username
        return username

# SSL certification
@app.route('/.well-known/acme-challenge/<filename>')
def acme_challenge(filename):
    # the path where win-acme will write challenge files
    return send_from_directory('.well-known/acme-challenge', filename)


@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory('static/backgrounds', filename)


@app.route('/')
@auth.login_required
def index():
    global client_username, openai_client, thread
    register_client_if_not_exists(client_username)
    dialog_messages = db.get_dialog_messages(client_username, config.dialog_window)
    thread = openai_client.beta.threads.create(messages=openai_utilities.dialog_messages_history(dialog_messages))
    return render_template('index.html')


# Sending favicon.ico to the browser
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(config.favicon_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# Transcription of audio fragments
@app.route('/transcribe', methods=['POST'])
@auth.login_required
def transcribe():
    global queue_empty

    print(f"\nStart of transcription of the fragment {current_time()}")

    audio_data = request.files['audio_data'].read()
    audio_file = BytesIO(audio_data)
    audio_queue.put(audio_file)
    queue_empty.clear()

    '''
    # Saving audio fragments
    global n
    n += 1
    a_file = "audio" + str(n) + ".webm"
    with open(a_file, "wb") as f:
        f.write(audio_data)
    '''

    return jsonify({'status': 'queued'})


# Clearing the current answer
def queue_clear():
    with sse_queue.mutex:
        sse_queue.queue.clear()


# Stop playback
@app.route('/stopplay', methods=['POST'])
@auth.login_required
def stopplay():
    global stop_play, stop_play_0, sse_queue
    queue_clear()
    stop_play = True
    stop_play_0 = True

    print("!!!!STOP_PLAY!!!!")

    return jsonify({'status': 'OK'})



# Generating an assistant's response
@app.route('/finalize', methods=['POST'])
@auth.login_required
def finalize():

    print(f"\nStart preparing the ASSISTANT's response {current_time()}")

    global full_text, thread, first_audio_file, stop_play, assistants_response_ready, sse_queue, run_id, client_username, finalize_event

    # 1. We signal to stop the old finalize if it is alive
    if not finalize_event.is_set():
        print(">>> A new finalize is started, we send a stop signal to the old one")
        finalize_event.set()
        # Now we wait for the old finalize to come out (timeout just in case)
        wait_cnt = 0
        while getattr(finalize_event, 'active', False):
            time.sleep(0.02)
            wait_cnt += 1
            if wait_cnt > 100:            # maximum 2 seconds of waiting...
                print(">>> Warning: old finalize did not complete in 2s!")
                break

    # 2. The signal has been reset, you can start a new processing
    finalize_event.clear()
    finalize_event.active = True             # sign: the stream is running

    try:
        event = {}
        #stop_play = False
        assistants_response_ready = False

        # Trigger for the first audio response from the assistant
        assistants_first_response = True


        '''
        if run_id != '':
    
            print("\n\n!!!PLAY_STOP_RUN!!! ASSISTANT")
            print(f"RUN_ID: {run_id}\n\n")
    
            assistants_response_ready = False
    
            try:
                #openai_utilities.cancel_run(thread, run_id)
                print('')
            except Exception as e:
    
                print(f"!!!COMPLETED RUN!!! ASSISTANT\n {e}")
        '''


        # Clearing the current answer
        queue_clear()

        # Selecting an audio "mute"
        #random_number = random.randint(0, len(first_audio_file) - 1)
        #sse_queue.put(first_audio_file[random_number])

        
        print("***STOP**** ASSISTANT", "\n")
        print(full_text, "\n")

        
        full_text_for_send = full_text

        try:
            run = openai_utilities.fetch_ai_response(thread, full_text)

            full_text = ' '
            ai_response = ""
            chunk_for_audio_response = ""
            chunk_call_function_response = ""

            for event in run:

                if finalize_event.is_set():
                    print("!!!PLAY_STOP!!!: received Event")
                    queue_clear()
                    break

                if event.event == 'thread.message.delta':
                    delta = openai_utilities.assistants_response(event)

                    chunk_for_audio_response += delta

                    #Creating audio fragments from a model's text response
                    if chunk_for_audio_response[-1:] in punctuation_mark_list and len(chunk_for_audio_response) > 10:

                        print(f"\nГОТОВО: chunk_for_audio_response ASSISTANT {current_time()}")

                        response_audio_file = openai_utilities.text_to_audio(chunk_for_audio_response)

                        if assistants_first_response is True:

                            print("\n\n!!!ASSISTANT'S RESPONSE IS READY!!! (in the ASSISTANT function)")

                            # Deleting an already loaded model response
                            queue_clear()

                            assistants_first_response = False

                        assistants_response_ready = True
                        ai_response += chunk_for_audio_response
                        chunk_for_audio_response = ""
                        if not finalize_event.is_set():
                            sse_queue.put(response_audio_file)

                            print(f"\nDONE: response_audio_file ASSISTANT {current_time()}")

                        else:

                            print("\n\n2____!!!PLAY_STOP!!! ASSISTANT")

                            # Clearing the current answer
                            queue_clear()
                            break

                try:
                    if event.event == 'thread.run.step.delta':
                        if event.data.delta.step_details.tool_calls[0].type != 'file_search' and event.data.delta.step_details.tool_calls[0].type != 'code_interpreter':
                            delta_call_function = openai_utilities.assistants_call_function_response(event)
                            chunk_call_function_response += delta_call_function

                            
                except Exception as e:

                    print(f"\nFailed function call: {e}\n")

            if chunk_call_function_response != "":
                # Search for JSON objects in the received string object
                json_objects = re.findall(r'\{.*?}', chunk_call_function_response)
                # Convert each JSON string into a Python object
                json_list = [json.loads(obj) for obj in json_objects]

                outputs_of_plugins = {}
                for obj in json_list:
                    if "plugin" in obj:
                        func = getattr(config, obj.get("plugin"), None)
                        if func:  # Checking that the function exists
                            outputs_of_plugins[obj.get("plugin")] = func(**obj)

                #print("\noutputs_of_plugins: ", outputs_of_plugins, "\n")

                with openai_utilities.RequiresActionFromTools().on_event(thread, event, outputs_of_plugins) as streaming:
                    for delta in streaming.text_deltas:

                        if finalize_event.is_set():

                            print("\n\n!!!PLAY_STOP!!! АССИСТЕНТА")

                            # Clearing the current answer
                            queue_clear()
                            break

                        chunk_for_audio_response += delta
                        #Creating audio fragments from a model's text response
                        if chunk_for_audio_response[-1:] in punctuation_mark_list and len(chunk_for_audio_response) > 10:

                            print(f"\nDONE: chunk_for_audio_response ASSISTANT {current_time()}")

                            response_audio_file = openai_utilities.text_to_audio(chunk_for_audio_response)

                            if assistants_first_response is True:

                                print("\n\n!!!ASSISTANT'S RESPONSE IS READY!!! (in the ASSISTANT function)")

                                # Deleting an already loaded model response
                                queue_clear()

                                assistants_first_response = False

                            assistants_response_ready = True
                            ai_response += chunk_for_audio_response
                            chunk_for_audio_response = ""
                            if not finalize_event.is_set():
                                sse_queue.put(response_audio_file)

                                print(f"\nDONE: response_audio_file ASSISTANT {current_time()}")

                            else:

                                print("\n\n3____!!!PLAY_STOP!!! ASSISTANT ")

                                # Clearing the current answer
                                queue_clear()
                                break


            #Creating the final audio fragment from the model's text response
            if chunk_for_audio_response != "":

                response_audio_file = openai_utilities.text_to_audio(chunk_for_audio_response)

                ai_response += chunk_for_audio_response
                if not finalize_event.is_set():
                    sse_queue.put(response_audio_file)
             
                else:
                    
                    # Clearing the current answer
                    queue_clear()


            print("\n")
        except Exception as e:
            print(e)
            return jsonify({'error finalize': str(e)})

        # Saving a dialogue to the database
        new_dialog_message = {"client": full_text_for_send, "assistant": ai_response, "date": datetime.now()}
        db.set_dialog_messages(
            client_username,
            db.get_dialog_messages(client_username, dialog_id=None) + [new_dialog_message],
            dialog_id=None
        )

        print(">>> finalize ended")

    finally:
        finalize_event.active = False    # we clear the work sign
    return jsonify({'full_text': full_text_for_send, 'ai_response': ai_response})




# Forming a model response
@app.route('/finalize_0', methods=['POST'])
@auth.login_required
def finalize_0():

    global full_text_0, first_audio_file, stop_play_0, assistants_response_ready, sse_queue, finalize_event_0

    if not finalize_event_0.is_set():
        finalize_event_0.set()
        wait_cnt = 0
        while getattr(finalize_event_0, 'active', False):
            time.sleep(0.02)
            wait_cnt += 1
            if wait_cnt > 100:            
                break

    finalize_event_0.clear()
    finalize_event_0.active = True             

    try:

        print(full_text_0, "\n")

        try:
            response = openai_utilities.fetch_ai_response_0(full_text_0)

            full_text_0 = ' '
            chunk_for_audio_response = ""

            for chunk in response:

                if assistants_response_ready is True:

                    break

                if finalize_event_0.is_set():

                    queue_clear()

                    break

                if chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content

                    chunk_for_audio_response += delta

                    if chunk_for_audio_response[-1:] in punctuation_mark_list and len(chunk_for_audio_response) > 10:

                        print(f"\nГОТОВО: chunk_for_audio_response МОДЕЛИ {current_time()}")

                        response_audio_file = openai_utilities.text_to_audio_0(chunk_for_audio_response)

                        chunk_for_audio_response = ""
                        if assistants_response_ready is True:

                            break

                        if not finalize_event_0.is_set():
                            sse_queue.put(response_audio_file)

                        else:
                            queue_clear()
                            break

            if chunk_for_audio_response != "":

                if assistants_response_ready is False:
                    response_audio_file = openai_utilities.text_to_audio(chunk_for_audio_response)

                    if not finalize_event_0.is_set():
                        sse_queue.put(response_audio_file)

                    else:

                        queue_clear()


            print("\n")
        except Exception as e:
            #full_text_0 = ' '
            print(e)
            return jsonify({'error finalize': str(e)})

        #full_text_0 = ' '

    finally:
        finalize_event_0.active = False    

    return jsonify({'status': 'Model answered'})



@app.route('/stream')
@auth.login_required
def stream():
    def generate():
        global n
        while True:
            try:
                if sse_queue.empty():
                    # Send an empty string to initiate a connection.
                    yield ":\n\n"
                else:
                    audio_html = sse_queue.get()
                    yield f"data: {audio_html}\n\n"

                    print(f"SENT TO BROWSER: {n}")
                    n += 1
                    #t = len(audio_html) * t_koef
                    #time.sleep(t)

            except GeneratorExit:
                # This exception occurs when the generator terminates.
                print("Client disconnected, stopping generator.")
                break
            except ssl.SSLEOFError as e:
                print(f"Error in SSE stream: {e}")
                logger.error(f"SSL EOF Error in SSE stream: {e}")
                break
            except OSError as e:
                # Ignoring errors caused by closing the connection
                if e.errno in [errno.EPIPE, errno.ECONNRESET]:
                    print(f"Connection closed by client: {e}")
                    logger.warning(f"Connection closed by client: {e}")
                    break
                else:
                    # For other OSErrors, throw an exception.
                    raise
            except Exception as e:
                print(f"Error in SSE stream: {e}")
                logger.error(f"Error in SSE stream: {e}")
                break

    return Response(generate(), mimetype='text/event-stream')


def process_audio_queue():
    global full_text, full_text_0, queue_empty
    while True:
        audio_file = audio_queue.get()
        audio_file.name = "audio.webm"
        #audio_file_size = audio_file.getbuffer().nbytes
        if audio_file is None:
            break
        try:
            queue_empty.clear()  # Clearing the event indicating that the transcription queue is not empty (reset to False)
            transcribed_text = openai_utilities.transcribe_audio(audio_file)
            if '!0!' in transcribed_text:
                transcribed_text = ''
            full_text += transcribed_text + " "
            full_text_0 += transcribed_text + " "

            print(f"\nEnd of transcription of fragment {current_time()} ### full_text & full_text_0:{full_text}")

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
        finally:
            audio_queue.task_done()
            # If the queue is empty after the current element is processed, the True event is set.
            if audio_queue.empty():
                queue_empty.set()


# Text recognition status
@app.route('/is_speech_recognized')
@auth.login_required
def is_speech_recognized():
    global full_text, full_text_0, queue_empty, first_audio_file
    # Selecting an audio "mute"
    #random_number = random.randint(0, len(first_audio_file) - 1)
    #sse_queue.put(first_audio_file[random_number])
    # Waiting for all transcribed fragments in the queue to finish

    queue_empty.wait(timeout=5)
    #queue_empty.wait()

    if len(full_text) >= 1 and all(symbol == ' ' for symbol in full_text):
        # If speech is not recognized, the signal is True
        full_text_0 = ' '
        full_text = ' '

        return jsonify({'no_speech': True})
    else:
        # If speech was recognized, the signal is False

        # Selecting an audio "mute"
        #random_number = random.randint(0, len(first_audio_file) - 1)
        #sse_queue.put(first_audio_file[random_number])

        return jsonify({'no_speech': False})


if __name__ == "__main__":
    waitings_jingles()
    threading.Thread(target=process_audio_queue, daemon=True).start()


    # Configuring CherryPy to Use a Flask Application
    cherrypy.tree.graft(app, '/')
    cherrypy.config.update({
        'server.socket_host': '100.100.100.100',  # YOUR IP address
        'server.socket_port': 100,           # YOUR PORT
        'server.ssl_module': 'builtin',        # Built-in SSL module
        'server.ssl_certificate': str(config.ssl_certificate_path),  # Path to SSL certificate
        'server.ssl_private_key': str(config.ssl_private_key_path),  # Path to the private key
        'server.thread_pool': 30,  # Number of threads to process requests.
        'server.socket_timeout': 60,  # Time in seconds to wait for data from the client
        'server.socket_queue_size': 10,  # Queue size
        'log.access_file': str(config.log_access_file_path),
        'log.error_file': str(config.log_error_file_path),
    })
    # Launch CherryPy
    cherrypy.engine.start()
    cherrypy.engine.block()
