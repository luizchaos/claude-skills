#!/usr/bin/env python3
"""Transcreve áudios/vídeos em português com faster-whisper.
Uso: python3 -I transcrever.py DIR_MODELO DIR_SAIDA arquivo1 [arquivo2 ...]
Variável opcional: PROMPT="vocabulário do caso"
"""
import sys, os, time, subprocess
import numpy as np
from faster_whisper import WhisperModel

model_dir, out_dir, files = sys.argv[1], sys.argv[2], sys.argv[3:]
m = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=os.cpu_count())
os.makedirs(out_dir, exist_ok=True)
PROMPT = os.environ.get("PROMPT", "Atendimento ao cliente. Ordem de serviço, protocolo, garantia.")
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    out = os.path.join(out_dir, name + ".txt")
    if os.path.exists(out):
        continue
    t = time.time()
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", f,
                          "-af", "highpass=f=80,dynaudnorm=f=150:g=15",
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    segs, info = m.transcribe(audio, language="pt", beam_size=5, vad_filter=True,
                              vad_parameters={"threshold": 0.35, "min_silence_duration_ms": 700},
                              condition_on_previous_text=False, no_repeat_ngram_size=3,
                              initial_prompt=PROMPT)
    lines, last = [], None
    for s in segs:
        txt = s.text.strip()
        if not txt or txt == last:
            continue
        last = txt
        mm, ss = divmod(int(s.start), 60)
        lines.append(f"[{mm:02d}:{ss:02d}] {txt}")
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"done {name} dur={info.duration:.0f}s took={time.time()-t:.0f}s", flush=True)
