#!/usr/bin/env python3
"""Generate the spoken steps as WAV files.

Drives libespeak-ng DIRECTLY rather than shelling out to the espeak-ng binary
(which is not installed and needs sudo). The `espeakng-loader` wheel ships its
own libespeak-ng.so plus the full voice data, so this runs with no system
install and no privileges.

Pauses between steps are baked into the audio via espeak's [[slnc N]] command,
so the rhythm is identical wherever the file is played.
"""
import ctypes, json, os, struct, sys, wave

VENV_SITE = "/home/alex/.tts-venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

LANGS = {
    "en":  ("en",  "English"),
    "cmn": ("cmn", "Mandarin"),
    "yue": ("yue", "Cantonese"),
    "hak": ("hak", "Hakka"),
}

# espeak_Initialize output modes
AUDIO_OUTPUT_RETRIEVAL = 0x02

class Speaker:
    """A minimal wrapper around the espeak-ng C API for synchronous synthesis."""

    def __init__(self):
        import espeakng_loader as el
        self.data = el.get_data_path()
        libp = el.get_library_path()
        if not os.path.exists(libp):
            sys.exit(f"loader library missing: {libp}")
        os.environ["ESPEAK_DATA_PATH"] = self.data
        self.lib = ctypes.CDLL(libp)

        self.lib.espeak_Initialize.restype = ctypes.c_int
        self.lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int,
                                               ctypes.c_char_p, ctypes.c_int]
        self.rate = self.lib.espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0,
                                               self.data.encode(), 0)
        if self.rate <= 0:
            sys.exit("espeak_Initialize failed")

        self.lib.espeak_SetVoiceByName.restype = ctypes.c_int
        self.lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]

        self._buf = []
        cb_t = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short),
                                ctypes.c_int, ctypes.c_void_p)
        def _cb(wav, n, ev):
            self._buf.extend(wav[:n])
            return 0
        self._cb = cb_t(_cb)
        self.lib.espeak_SetSynthCallback.argtypes = [cb_t]
        self.lib.espeak_SetSynthCallback(self._cb)

        self.lib.espeak_Synth.argtypes = [ctypes.c_char_p, ctypes.c_size_t,
                                          ctypes.c_uint, ctypes.c_int,
                                          ctypes.c_uint, ctypes.c_uint,
                                          ctypes.c_void_p]

    def say(self, text, voice="en"):
        if self.lib.espeak_SetVoiceByName(voice.encode()) != 0:
            # fall back to the base language if the exact voice is unavailable
            base = voice.split("-")[0]
            if self.lib.espeak_SetVoiceByName(base.encode()) != 0:
                sys.exit(f"voice not available: {voice}")
        self._buf = []
        # position 0, no flags, no end pause, no word gap
        rc = self.lib.espeak_Synth(text.encode("utf-8"), 0, 0, 0, 0, 0, None)
        if rc != 0 or not self._buf:
            return None
        return b"".join(struct.pack("<h", s) for s in self._buf)


def write_wav(path, pcm, rate):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "narration_en.json")
    data = json.load(open(src, encoding="utf-8"))
    spk = Speaker()
    print(f"espeak-ng ready at {spk.rate} Hz\n")

    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    voice, label = LANGS.get(lang, LANGS["en"])
    outdir = os.path.join(here, "audio", lang)
    os.makedirs(outdir, exist_ok=True)

    made = []
    for st in data["steps"]:
        spoken = st.get("spoken") or f"Step {st['index']}. {st['title']}. {st['text']}"
        pcm = spk.say(spoken, voice)
        if not pcm:
            print(f"  step {st['index']:2}  FAILED")
            continue
        path = os.path.join(outdir, f"step{st['index']:02d}.wav")
        write_wav(path, pcm, spk.rate)
        made.append((st["index"], len(pcm), len(pcm) / 2 / spk.rate))
        print(f"  step {st['index']:2}  {len(pcm):>7} bytes  {len(pcm)/2/spk.rate:5.1f} s")

    total = sum(m[2] for m in made)
    print(f"\n{label}: {len(made)} files, {total:.1f} s total -> {outdir}")


if __name__ == "__main__":
    main()
