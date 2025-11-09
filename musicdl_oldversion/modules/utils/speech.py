'''
Function:
    语音识别模块
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import time


'''语音识别模块'''
class SpeechRecognition():
    def __init__(self, app_id, api_key, secret_key, **kwargs):
        from aip import AipSpeech
        self.aipspeech_api = AipSpeech(app_id, api_key, secret_key)
        self.speech_path = kwargs.get('speech_path', 'recording.wav')
        assert self.speech_path.endswith('.wav'), 'only support audio with wav format'
    '''录音'''
    def record(self, sample_rate=16000):
        import speech_recognition as sr
        rec = sr.Recognizer()
        with sr.Microphone(sample_rate=sample_rate) as source:
            audio = rec.listen(source)
        with open(self.speech_path, 'wb') as fp:
            fp.write(audio.get_wav_data())
    '''识别'''
    def recognition(self):
        assert os.path.exists(self.speech_path)
        with open(self.speech_path, 'rb') as fp:
            content = fp.read()
        result = self.aipspeech_api.asr(content, 'wav', 16000, {'dev_pid': 1536})
        text = result['result'][0]
        return text
    '''合成并说话'''
    def synthesisspeak(self, text=None, audiopath=None):
        assert text is None or audiopath is None
        import pygame
        if audiopath is None:
            audiopath = f'recording_{time.time()}.mp3'
            result = self.aipspeech_api.synthesis(
                text, 'zh', 1, 
                {'spd': 4, 'vol': 5, 'per': 4}
            )
            if not isinstance(result, dict):
                with open(audiopath, 'wb') as fp:
                    fp.write(result)
            pygame.mixer.init()
            pygame.mixer.music.load(audiopath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(1)
        else:
            pygame.mixer.init()
            pygame.mixer.music.load(audiopath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(1)