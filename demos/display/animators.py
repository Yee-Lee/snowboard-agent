import math
import time
import subprocess
import threading
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

from sbd.core.display.rendering.animation import register

# --- Fade Animator ---
@register("fade_demo")
class FadeAnimator:
    """Fades an image in and out."""
    def __init__(self, width: int, height: int, image_path: str = "demos/display/assets/photo.jpg"):
        self.width = width
        self.height = height
        try:
            self.image = Image.open(image_path).convert("RGB").resize((width, height))
        except Exception:
            self.image = Image.new("RGB", (width, height), (100, 100, 100))
            
    def render(self, elapsed_time: float) -> Image.Image:
        # 0.0 -> 2.0 sec: Fade in (0 to 255)
        # 2.0 -> 4.0 sec: Fade out (255 to 0)
        # Loop every 4 seconds
        cycle_time = elapsed_time % 4.0
        
        if cycle_time < 2.0:
            alpha = int((cycle_time / 2.0) * 255)
        else:
            alpha = int(((4.0 - cycle_time) / 2.0) * 255)
            
        canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        mask = Image.new("L", (self.width, self.height), alpha)
        canvas.paste(self.image, (0, 0), mask)
        return canvas

# --- Chat Animator ---
@register("chat_demo")
class ChatAnimator:
    """Simulates a scrolling chat dialog."""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        try:
            self.font = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 12)
        except IOError:
            self.font = ImageFont.load_default()
            
        self.colors = {
            "System": (120, 120, 120),
            "Ned": (255, 200, 50),
            "Peter": (255, 80, 80)
        }
        
        self.script = [
            ("System", "[System] Intercepting..."),
            ("Ned", "You're Spider-Man!"),
            ("Peter", "No, no! I'm not!"),
            ("Ned", "You were on the ceiling!"),
            ("Peter", "I was cleaning!"),
            ("System", "----------------"),
            ("System", "[系統] 啟動翻譯模組..."),
            ("Ned", "你是蜘蛛人！"),
            ("Peter", "不不不！我不是！"),
            ("Ned", "你剛剛爬在天花板耶！"),
            ("Peter", "我剛剛在打掃！"),
        ]
        
        self.line_height = 14
        self.chars_per_sec = 25.0
        
    def render(self, elapsed_time: float) -> Image.Image:
        canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        
        total_chars_allowed = int(elapsed_time * self.chars_per_sec)
        
        # Calculate how many lines we have and auto-scroll if needed
        # (For simplicity, we just type them out. If it overflows, it scrolls up)
        
        chars_used = 0
        drawn_lines = []
        
        for speaker, text in self.script:
            line_text = f"{speaker}: {text}" if speaker != "System" else text
            line_len = len(line_text)
            
            if chars_used + line_len <= total_chars_allowed:
                drawn_lines.append((line_text, self.colors.get(speaker, (255,255,255))))
                chars_used += line_len
            else:
                remaining_chars = total_chars_allowed - chars_used
                if remaining_chars > 0:
                    current_text = line_text[:remaining_chars]
                    if int(elapsed_time * 4) % 2 == 0:
                        current_text += "_"
                    drawn_lines.append((current_text, self.colors.get(speaker, (255,255,255))))
                break
                
        # Scroll up if there are more lines than fit on screen
        max_lines = self.height // self.line_height
        if len(drawn_lines) > max_lines:
            drawn_lines = drawn_lines[-max_lines:]
            
        y_pos = 5
        for text, color in drawn_lines:
            draw.text((5, y_pos), text, font=self.font, fill=color)
            y_pos += self.line_height
            
        return canvas

# --- Video Animator ---
@register("video_demo")
class VideoAnimator:
    """Reads frames from a video file sequentially using an internal thread."""
    def __init__(self, width: int, height: int, path: str = "demos/display/assets/countdown.mp4"):
        self.width = width
        self.height = height
        self.path = path
        
        self.latest_frame = Image.new("RGB", (width, height))
        self.running = True
        self.thread = threading.Thread(target=self._decode_loop, daemon=True)
        self.thread.start()
        
    def _decode_loop(self):
        frame_size = self.width * self.height * 3
        cmd = [
            "ffmpeg", "-i", self.path, "-f", "image2pipe", "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24", "-s", f"{self.width}x{self.height}", "-"
        ]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            while self.running:
                raw = proc.stdout.read(frame_size)
                if not raw or len(raw) != frame_size:
                    # EOF, loop the video
                    proc.terminate()
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    continue
                
                img = Image.frombytes("RGB", (self.width, self.height), raw)
                self.latest_frame = img
                time.sleep(1/30.0)
        except Exception:
            pass

    def render(self, elapsed_time: float) -> Image.Image:
        return self.latest_frame

@register("mow_video_demo")
class MowVideoAnimator(VideoAnimator):
    """Plays mow.mp4."""
    def __init__(self, width: int, height: int):
        super().__init__(width, height, path="demos/display/assets/mow.mp4")
