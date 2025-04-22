from flask import Flask, request, jsonify, send_from_directory
import openai
import boto3
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

polly = boto3.client("polly", region_name=os.getenv("AWS_REGION"),
                     aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

@app.route("/process-voice", methods=["POST"])
def process_voice():
    audio_file = request.files["audio"]
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    text = transcript["text"]

    prompt = f"""You are a real estate assistant. Given this voice command: '{text}', extract intent and important info:
Return JSON like this:
{{"intent": "...", "address": "...", "datetime": "...", "action": "..."}}"""
    gpt_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    parsed = gpt_response.choices[0].message["content"]

    speech_response = polly.synthesize_speech(Text="Got it! I'm processing your request.",
                                               OutputFormat="mp3", VoiceId="Joanna")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_path = Path(temp_file.name)
    temp_path.write_bytes(speech_response["AudioStream"].read())

    return jsonify({
        "transcript": text,
        "intent": parsed,
        "audio_url": f"/audio/{temp_path.name.split('/')[-1]}"
    })

@app.route("/audio/<filename>")
def get_audio(filename):
    return send_from_directory("static", filename)
