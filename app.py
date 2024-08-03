from flask import Flask, request, render_template_string, jsonify
import pyaudio
import wave
import threading
import speech_recognition as sr
import os
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

app = Flask(__name__)

# Configuration
MISTRAL_API_KEY = '2kc7kSGnUvpF0s3sIlw3rH2olnd4DNl2'
model = "mistral-large-latest"

# Recording settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Global flag and buffer to control recording
recording = False
frames = []

# Recognizer instance
recognizer = sr.Recognizer()

# HTML template
HTML_TEMPLATE = '''
<!doctype html>
<html>
<head>
    <title>Speech to Text with Analysis</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        body {
            background: linear-gradient(120deg, #2a2a72, #009ffd);
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            font-family: Arial, sans-serif;
            margin: 0;
        }
        h1 {
            margin-bottom: 20px;
        }
        button {
            padding: 15px 30px;
            margin: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        #start-btn {
            background-color: red;
            color: white;
        }
        #stop-btn {
            background-color: green;
            color: white;
        }
        #stop-btn:disabled {
            background-color: gray;
        }
        .hidden {
            display: none;
        }
        .loader {
            width: 20px;
            aspect-ratio: 1;
            border-radius: 50%;
            background: #000;
            box-shadow: 0 0 0 0 #0004;
            animation: l2 1.5s infinite linear;
            position: relative;
        }
        .loader:before,
        .loader:after {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: inherit;
            box-shadow: 0 0 0 0 #0004;
            animation: inherit;
            animation-delay: -0.5s;
        }
        .loader:after {
            animation-delay: -1s;
        }
        @keyframes l2 {
            100% { box-shadow: 0 0 0 40px #0000; }
        }
        .processing-loader {
            width: 50px;
            padding: 8px;
            aspect-ratio: 1;
            border-radius: 50%;
            background: #25b09b;
            --_m: 
                conic-gradient(#0000 10%,#000),
                linear-gradient(#000 0 0) content-box;
            -webkit-mask: var(--_m);
                    mask: var(--_m);
            -webkit-mask-composite: source-out;
                    mask-composite: subtract;
            animation: l3 1s infinite linear;
        }
        @keyframes l3 {
            to { transform: rotate(1turn); }
        }
        #analysis {
            color: #9bff9b; /* Lighter green */
        }
    </style>
</head>
<body>
    <h1>Candidate Project Analyser.</h1>
    <button id="start-btn">Start Recording</button>
    <button id="stop-btn" disabled>Stop Recording</button>
    <div id="recording" class="hidden"><div class="loader"></div> Recording...</div>
    <div id="loading" class="hidden"><div class="processing-loader"></div> Processing...</div>
    <div id="transcription"></div>
    <div id="analysis"></div>
    <script>
        $('#start-btn').click(function() {
            $.get('/start_recording', function(data) {
                $('#start-btn').attr('disabled', true);
                $('#stop-btn').attr('disabled', false);
                $('#recording').removeClass('hidden');
                $('#transcription').text('');
                $('#analysis').text('');
            });
        });

        $('#stop-btn').click(function() {
            $.get('/stop_recording', function(data) {
                $('#start-btn').attr('disabled', false);
                $('#stop-btn').attr('disabled', true);
                $('#recording').addClass('hidden');
                $('#loading').removeClass('hidden');
                setTimeout(function() {
                    $('#loading').addClass('hidden');
                    $('#transcription').text('Transcription: ' + data.transcription);
                    $('#analysis').text('Analysis: ' + data.analysis);
                }, 5000); // simulate processing delay
            });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_recording')
def start_recording():
    global recording, frames
    recording = True
    frames = []
    threading.Thread(target=record_audio).start()
    return jsonify(status='recording')

@app.route('/stop_recording')
def stop_recording():
    global recording
    recording = False
    save_audio()
    transcription = transcribe_audio()
    analysis = analyze_transcription(transcription)
    return jsonify(transcription=transcription, analysis=analysis)

def record_audio():
    global recording, frames
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    while recording:
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

def save_audio(filename='output.wav'):
    global frames
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def transcribe_audio(filename='output.wav'):
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return ""
        except sr.UnknownValueError:
            print("Unknown error occurred")
            return ""

def analyze_transcription(transcription):
    client = MistralClient(api_key=MISTRAL_API_KEY)
    
    messages = [
        ChatMessage(role="user", content=f"analyse the {transcription}, give a score out of 10 based on the description, and the answers given to the questions. And a word on how good it was. Nothing extra.")
    ]

    chat_response = client.chat(
        model=model,
        messages=messages,
    )

    return chat_response.choices[0].message.content

if __name__ == '__main__':
    app.run(debug=True)
