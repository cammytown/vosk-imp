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
    audio_queue: queue.Queue
    device: Optional[str] = None
    samplerate: Optional[int] = None
    model: Optional[Model] = None
    recognizer: Optional[KaldiRecognizer] = None

    dump_filename: Optional[str] = None
    callback = None
    input_stream: Optional[sd.RawInputStream] = None

    def __init__(self,
                 device=None,
                 samplerate=None,
                 model_path=None,
                 filename=None):
        self.audio_queue = queue.Queue()
        self.device = device
        self.samplerate = samplerate
        self.model_path = model_path
        self.dump_filename = filename

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

        if not self.recognizer:
            self.recognizer = KaldiRecognizer(self.model, self.samplerate)

    def update(self):
        assert self.recognizer is not None

        data = self.audio_queue.get()

        if data is None:
            print("VoskImp: No data, exiting") #@TODO remove
            return

        if self.recognizer.AcceptWaveform(data):
            result_string = self.recognizer.Result()
            data = json.loads(result_string)

            if(data["text"] == ""):
                return

            if(data["text"] == "huh"):
                return

            print(data["text"])

            if self.callback is not None:
                self.callback(data["text"])

            return data["text"]

        else:
            #@REVISIT
            pass

        return None

    def start(self, callback = lambda text: print(text)):
        self.setup()

        # if self.dump_filename:
        #     dump_file = open(self.dump_filename, mode="wb", encoding="utf-8")
        # else:
        #     dump_file = None

        # signal.signal(signal.SIGINT, self.stop)
        # signal.signal(signal.SIGTERM, self.stop)

        print("VoskImp: Starting input stream") #@TODO remove

        self.input_stream =  sd.RawInputStream(samplerate=self.samplerate,
                                               blocksize=8000,
                                               device=self.device,
                                               dtype="int16",
                                               channels=1,
                                               callback=self.input_callback)
        self.input_stream.start()


            # while True:
            #     data = self.update()

            #     if dump_file is not None:
            #         dump_file.write(data)

    def stop(self, signum=None, frame=None):
        # print("Stopping VoskImp")

        if self.input_stream is not None:
            self.input_stream.close()

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

