import sys
import wave
import numpy as np

def process_audio(input_file, output_file, multiplier):
    # 打開原始錄音檔
    with wave.open(input_file, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(params.nframes)
    
    # 將二進位音訊資料轉為 NumPy 陣列 (S16_LE 格式對應 int16)
    audio_data = np.frombuffer(frames, dtype=np.int16)
    
    # 進行數位放大
    # 轉成 float 運算避免溢位
    amplified_data = audio_data.astype(np.float32) * multiplier
    
    # 限制數值範圍在 16-bit 上下限之間，防止嚴重破音 (Clipping)
    amplified_data = np.clip(amplified_data, -32768, 32767)
    
    # 轉回 int16 準備寫入
    final_audio = amplified_data.astype(np.int16)
    
    # 寫入放大的新音檔
    with wave.open(output_file, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(final_audio.tobytes())

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 amplify.py <input.wav> <output.wav> <multiplier>")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    mult = float(sys.argv[3])
    
    process_audio(in_file, out_file, mult)
