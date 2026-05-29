import dotenv
import pathlib
from pathlib import Path
from plugins.weather import weather, weather_json  # Плагин погоды
from plugins.ddg_web_search import web_search, web_search_json  # Плагин web поиска


# Loading .env config
config_path = Path(pathlib.Path.cwd(), "config")
config_env = dotenv.dotenv_values(config_path / ".env")
favicon_path = Path(pathlib.Path.cwd())
prompt_for_model_path = Path(pathlib.Path.cwd(), "config/Prompt_for_model.txt")
prompt_for_assistant_path = Path(pathlib.Path.cwd(), "config/Prompt_for_assistant.txt")
prompt_for_transcribe_path = Path(pathlib.Path.cwd(), "config/Prompt_for_transcribe.txt")
plugins_path = Path(pathlib.Path.cwd(), "plugins")
waitings_jingles_path = Path(pathlib.Path.cwd(), "jingles/wait_")
ssl_certificate_path = Path(pathlib.Path.cwd(), "certificate.crt")
ssl_private_key_path = Path(pathlib.Path.cwd(), "private.key")
log_access_file_path = Path(pathlib.Path.cwd(), "logs/access.log")
log_error_file_path = Path(pathlib.Path.cwd(), "logs/error.log")

# config parameters
username_1 = config_env["username_1"] if "username_1" in config_env else ""
password_1 = config_env["password_1"] if "password_1" in config_env else ""
username_2 = config_env["username_2"] if "username_2" in config_env else ""
password_2 = config_env["password_2"] if "password_2" in config_env else ""

api_key = config_env["api_key"] if "api_key" in config_env else ""
assistant = config_env["assistant"] if "assistant" in config_env else ""
proxies = config_env["proxies"] if "proxies" in config_env else None
assistant_name = config_env["assistant_name"] if "assistant_name" in config_env else "Agent"
#instructions = config_env["instructions"] if "instructions" in config_env else ""
model_name = config_env["model_name"] if "model_name" in config_env else "gpt-4o-mini"
assistants_model = config_env["assistants_model"] if "assistants_model" in config_env else "gpt-4o-mini"
assistant_response_format = config_env["response_format"] if "response_format" in config_env else None
transcription_model = config_env["transcription_model"] if "transcription_model" in config_env else "whisper-1"
tts_model = config_env["tts_model"] if "tts_model" in config_env else "tts-1"
voice = config_env["voice"] if "voice" in config_env else "nova"
audio_response_format = config_env["audio_response_format"] if "audio_response_format" in config_env else "opus"
temperature = float(config_env["temperature"]) if "temperature" in config_env else None
top_p = float(config_env["top_p"]) if "top_p" in config_env else None
speech_speed = float(config_env["speech_speed"]) if "speech_speed" in config_env else 1.0
dialog_window = int(config_env["dialog_window"]) if "dialog_window" in config_env else 0
plugins = [plugin.strip() for plugin in config_env["plugins"].split(",")] if "plugins" in config_env else []
tools = [globals()[plugin+"_json"] for plugin in plugins]  # Используются в модуле assistant_update.py

mongodb_uri = f"mongodb://{config_env['MONGODB_USERNAME']}:" \
              f"{config_env['MONGODB_PASSWORD']}@{config_env['MONGODB_IP']}:" \
              f"{config_env['MONGODB_PORT']}/?authSource={config_env['MONGODB_NAME']}"

with prompt_for_model_path.open('r', encoding='utf-8') as file:
    prompt_for_model = file.read()

with prompt_for_assistant_path.open('r', encoding='utf-8') as file:
    prompt_for_assistant = file.read()

with prompt_for_transcribe_path.open('r', encoding='utf-8') as file:
    prompt_for_transcribe = file.read()
