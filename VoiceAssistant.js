import React, { useState } from 'react';

function VoiceAssistant() {
  const [response, setResponse] = useState(null);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    let audioChunks = [];

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      const formData = new FormData();
      formData.append("audio", audioBlob, "input.wav");

      const res = await fetch("/process-voice", { method: "POST", body: formData });
      const json = await res.json();
      setResponse(json);
      const audio = new Audio(json.audio_url);
      audio.play();
    };

    mediaRecorder.start();
    setTimeout(() => mediaRecorder.stop(), 5000);
  };

  return (
    <div>
      <button onClick={startRecording}>Mic Speak</button>
      {response && (
        <div>
          <p><b>Transcript:</b> {response.transcript}</p>
          <pre>{response.intent}</pre>
        </div>
      )}
    </div>
  );
}

export default VoiceAssistant;
