#!/usr/bin/env python3

import queue
import appdirs
import sys
import json
import signal
from typing import Optional
import sounddevice as sd

from vosk import Model, KaldiRecognizer

class VoskImp:
    model: Optional[Model] = None

    def __init__(self,
                 device=None,
                 samplerate=None,
                 model_path=None,
                 filename=None):
        self.audio_queue = queue.Queue()
        self.device = device
        self.samplerate = samplerate
        self.model_path = model_path
        self.filename = filename

    def input_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.audio_queue.put(bytes(indata))

    def setup(self):
        # Set default args…
        if self.device is None:
            # Use default device
            #@TODO-3 better way of determining default device

            # self.device = sd.default.device[0]
            # self.device = 'pipewire'
            self.device = 'pulse'
            pass

        if self.samplerate is None:
            device_info = sd.query_devices(self.device, "input")
            # soundfile expects an int, sounddevice provides a float:
            self.samplerate = int(device_info["default_samplerate"])

        if not self.model:
            if self.model_path is None:
                self.model = Model(lang="en-us")

                #@TODO temporary:
                # model_name = "vosk-model-small-en-us"
                # model_path = appdirs.user_data_dir("VoskImp", "VoskImp")
                # self.model = Model(f"{model_path}/{model_name}")
            else:
                self.model = Model(self.model_path)


    def run(self, callback = lambda text: print(text)):
        self.setup()

        if self.filename:
            dump_file = open(self.filename, mode="wb", encoding="utf-8")
        else:
            dump_file = None

        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                               device=self.device, dtype="int16", channels=1,
                               callback=self.input_callback):
            print("#" * 80)
            print("Press Ctrl+C to stop the recording")
            print("#" * 80)

            recognizer = KaldiRecognizer(self.model, self.samplerate)

            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)

            while True:
                data = self.audio_queue.get()

                if data is None:
                    print("Exiting...")
                    break

                if recognizer.AcceptWaveform(data):
                    result_string = recognizer.Result()
                    data = json.loads(result_string)

                    if(data["text"] == ""):
                        continue

                    if(data["text"] == "huh"):
                        continue

                    callback(data["text"])
                else:
                    pass

                if dump_file is not None:
                    dump_file.write(data)

    def stop(self, signum=None, frame=None):
        self.audio_queue.put(None)

    # def __del__(self):
    #     self.stop()

    # def __exit__(self, exc_type, exc_value, traceback):
    #     self.stop()

#@REVISIT probably remove:
if __name__ == "__main__":
    vosk_imp = VoskImp()
    try:
        vosk_imp.run()
    except KeyboardInterrupt:
        print("\nDone")
        sys.exit(0)
    except Exception as e:
        print("vosk server exited with error below:")
        sys.exit(type(e).__name__ + ": " + str(e))

