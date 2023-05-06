from vosk_imp import VoskImp

def stt_callback(text):
    print(text)

VoskImp().run(stt_callback)
