# 在 Python 中生成 Base64
import base64

# 读取 WAV 文件并转换为 Base64
with open("audioDAIHaoyu11255851570.wav", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode()

# 写入到文本文件
with open("audio_base64.txt", "w", encoding="utf-8") as f:
    f.write(audio_base64)

print(f"✅ Base64 编码已保存到 audio_base64.txt，长度: {len(audio_base64)}")