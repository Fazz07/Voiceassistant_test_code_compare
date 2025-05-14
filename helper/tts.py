import os
import json
import random
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, AudioConfig, SpeechSynthesisOutputFormat
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

public_folder = os.path.join(os.getcwd(), 'public')

# Load Azure Speech API credentials
key = os.getenv("AZURE_KEY")
region = os.getenv("AZURE_REGION")

blend_shape_names = ["eyeBlinkLeft",
    "eyeLookDownLeft",
    "eyeLookInLeft",
    "eyeLookOutLeft",
    "eyeLookUpLeft",
    "eyeSquintLeft",
    "eyeWideLeft",
    "eyeBlinkRight",
    "eyeLookDownRight",
    "eyeLookInRight",
    "eyeLookOutRight",
    "eyeLookUpRight",
    "eyeSquintRight",
    "eyeWideRight",
    "jawForward",
    "jawLeft",
    "jawRight",
    "jawOpen",
    "mouthClose",
    "mouthFunnel",
    "mouthPucker",
    "mouthLeft",
    "mouthRight",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthStretchLeft",
    "mouthStretchRight",
    "mouthRollLower",
    "mouthRollUpper",
    "mouthShrugLower",
    "mouthShrugUpper",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    "browDownLeft",
    "browDownRight",
    "browInnerUp",
    "browOuterUpLeft",
    "browOuterUpRight",
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    "noseSneerLeft",
    "noseSneerRight",
    "tongueOut",
    "headRoll",
    "leftEyeRoll",
    "rightEyeRoll",
    ]

# SSML Template for Azure TTS
SSML_TEMPLATE = """
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">
    <voice name="en-US-AriaNeural">
        <mstts:viseme type="FacialExpression"/>
        {text}
    </voice>
</speak>
"""

class SpeechService:

    @staticmethod
    async def text_to_speech(text):
        # Generate SSML
        ssml = SSML_TEMPLATE.format(text=text)
        
        # Setup Speech SDK
        speech_config = SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_output_format = SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        
        # Generate a random file name for output
        random_string = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
        filename = f"./public/speech-{random_string}.mp3"
        
        # Setup audio output config
        audio_config = AudioConfig(filename=filename)
        
        blend_data = []
        time_step = 1 / 60
        timestamp = 0

        def viseme_received_handler(evt):
            nonlocal timestamp
            print("Viseme event received!")  # Debugging output
            print(f"Audio offset: {evt.audio_offset / 10000} ms, Viseme ID: {evt.viseme_id}")  # Log audio offset and viseme id for debugging

            try:
                # Parse the animation data (assuming it's JSON)
                animation = json.loads(evt.animation) if evt.animation else {}
                print(f"Animation Data: {animation}")  # Debugging output
                                
                for blend_array in animation.get("BlendShapes", []):
                    blend = {}
                    for i, shape_name in enumerate(blend_shape_names):
                        blend[shape_name] = blend_array[i]
                    
                    blend_data.append({
                        "time": timestamp,
                        "blendshapes": blend
                    })
                    timestamp += time_step
            except Exception as e:
                print(f"Error parsing animation data: {e}")

        # Setup synthesizer
        synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        # Register the event handler
        synthesizer.viseme_received.connect(viseme_received_handler)
        
        # Start speech synthesis asynchronously, but block until completion
        try:
            # Synchronously wait for the speech synthesis to finish
            result = synthesizer.speak_ssml_async(ssml).get()
            
            print("blendData: ", blend_data)
            print(f'filename: /speech-{random_string}.mp3')
            # Return result after speech synthesis finishes
            return {"blendData": blend_data, "filename": f"/speech-{random_string}.mp3"}
        except Exception as e:
            print(f"Error during synthesis: {e}")
            return {"error": str(e)}



















    # @staticmethod
    # async def text_to_speech(text, voice=None):
    #     filename = "speech-111.mp3"
    #     file_path = os.path.join(public_folder, filename)

    #     # Check if the file exists
    #     if not os.path.exists(file_path):
    #         return {"error": f"File {filename} not found in the public folder"}

    #     data_path = os.path.join(public_folder, 'blendDataResponse.json')
        
    #     if not os.path.exists(data_path):
    #         return {"error": "data.json not found in the public folder"}
    
    #     with open(data_path, 'r') as file:
    #         data = json.load(file)

    #     # Return blendData and filename (relative to the public directory)
    #     return {
    #         "blendData": data.get("blendData"),
    #         "filename": f"/{filename}"  # URL path to serve the file
    #     }