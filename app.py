from quart import Quart, jsonify, request, Response, send_file, render_template, after_this_request
from quart_cors import cors
from dotenv.main import load_dotenv
import requests
from helper.chat import ChatService
from helper.tts import SpeechService
from langchain.memory import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
import os
import io
import asyncio
from gtts import gTTS
import pyttsx3
import time
from langdetect import detect
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig, AudioDataStream, ResultReason
from azure.cognitiveservices.speech.audio import AudioOutputConfig


load_dotenv()

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_SPEECH_URL=os.getenv("AZURE_SPEECH_URL")

app = Quart(__name__)
cors(app)

AUDIO_DIR = "Audio_Files"
os.makedirs(AUDIO_DIR, exist_ok=True)

public_folder = os.path.join(os.getcwd(), 'public')

session_histories = {}
session_questions = {}

def get_or_create_chat_message_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in session_histories:
        session_histories[session_id] = ChatMessageHistory()
    return session_histories[session_id]


@app.route('/')
async def index():
    return await render_template('Conversational_Agent.html')


chat = ChatService()
speech = SpeechService()

@app.route('/speech_conversion', methods=['POST'])
async def speech_to_text():
    try:
        request_files = await request.files
        request_form = await request.form

        if 'audio' not in request_files:
            return jsonify({"error": "No audio provided"}), 400

        audio_file = request_files['audio']
        language = request_form.get('lang', 'en-US')

        if language == 'en':
            language = 'en-US'

        audio_data = audio_file.read()

        headers = {
            "Ocp-Apim-Subscription-Key": SPEECH_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(url=f'{AZURE_SPEECH_URL}?language={language}', headers=headers, data=audio_data)

        if response.status_code == 200:
            result = response.json()
            recognized_text = result.get('DisplayText', '')
            return jsonify({"text": recognized_text}), 200
        else:
            return jsonify({"error": f"An internal error occurred: {response.status_code}, {response.text}  "})
        
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    
    except Exception as e:
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500


@app.route('/clear_session_id')
async def clear_session_id():
    try:
        data = request.get_json()
        session_id = data.get("session_id", "")

        if session_id in session_histories:
            print("session_histories before clearance :", session_histories)
            del session_histories[session_id]
            print("session_histories after clearance :", session_histories)
            return jsonify({"id": "Session history cleared"}), 200
        else:
            return jsonify({"id": "Session ID not found"}), 404

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500


@app.route('/tts', methods=['POST'])
async def text_to_speech():
    try:
        start_time = time.time()
        data = await request.get_json()
        text = data.get("text", "")
        language = data.get("language", "en")
        session_id = data.get("session_id", "")

        start_time_str = str(start_time)
        time_partition = start_time_str.rpartition(".")[-1]

        if not text:
            return jsonify({"error": "No text provided for TTS"}), 400

        speech_config = SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        
        if language == "ar" or language == "ur":
            print("Arabic!!!", language)
            speech_config.speech_synthesis_language = "ar-QA"
            speech_config.speech_synthesis_voice_name = "ar-QA-MoazNeural"
        else:
            print("English!!!", language)
            speech_config.speech_synthesis_language = "en-US"
            speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

        audio_config = speechsdk.audio.AudioOutputConfig(filename=f"Audio_Files/{session_id}_{time_partition}_{language}.wav")

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return await send_file(f"Audio_Files/{session_id}_{time_partition}_{language}.wav", mimetype='audio/wav')
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details

            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    return jsonify({"error": "Please make sure the details are correct!"}), 400

    except Exception as e:
        print(f"Error in TTS endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/process_speech', methods=['POST'])
async def process_speech():
    try:
        data = await request.get_json()
        question = data.get("speech_text", "")
        session_id = data.get("session_id", "")

        if not question:
            return jsonify({"issue": "Please provide your question!"})
        else:
            language = detect(question)
            
            result = await chat.do_chat(question, get_or_create_chat_message_history, session_id, language)
            
            if result:
                responselanguage = detect(result)
                return jsonify({"message": result,
                                "language": responselanguage})
            else:
                return jsonify({"message": "Our system encountered an issue, we'll get back to you shortly!"})

    except Exception as e:
        return jsonify({"message": "Please make sure the input is valid!"}), 400


@app.route('/synthesize', methods=['POST'])
async def synthesize_speech():
    data = await request.get_json()
    print(f"Received data: {data}")
    
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "Text is required"}), 400
    
    print(f"Received text: {text}")
    
    try:
        result = await SpeechService.text_to_speech(text=text)
        return jsonify(result)
    except Exception as e:
        print(f"Error during speech synthesis: {e}")
        return jsonify({"error": "An error occurred during speech synthesis."}), 500


@app.route('/<filename>', methods=['GET'])
async def serve_audio(filename):
    file_path = os.path.join(public_folder, filename)
    
    if os.path.exists(file_path):
        return await send_file(file_path)
    else:
        return jsonify({"error": "File not found"}), 404


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=7000)
