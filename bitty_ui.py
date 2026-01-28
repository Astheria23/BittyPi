import pygame
import time
import threading
import os
import random
import math
import asyncio
from ears import Ears
import brain
from metrics import get_remote_metrics, get_local_metrics

# Inisialisasi
pygame.init()
pygame.mixer.init()
#os.environ["DISPLAY"] = ":0" 

screen_width = 480
screen_height = 320
screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
clock = pygame.time.Clock()

# Warna
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# --- Config ---
HIT_WINDOW = 0.8
HIT_RADIUS = 100
HOLD_THRESHOLD = 0.4
JITTER_GRACE = 0.15

# --- State Bitty ---
curr_eye_h, curr_eye_x = 0.0, 100.0 
curr_eye_pos_x = 240.0
curr_mouth_w, curr_mouth_h = 0.0, 0.0
curr_offset_y = 0.0 

target_eye_h, target_eye_x = 0.0, 100.0
target_eye_pos_x = 240.0
target_mouth_w, target_mouth_h = 0.0, 0.0
target_offset_y = 0.0
base_eye_h = 60.0

running = True
current_emotion = "startup"
saved_emotion = "idle"

# Tracker Logic
hit_taps = 0           # Ngitung tap (1-3)
hit_cycle_count = 0    # Ngitung berapa kali kena "hit" (3 cycle = sad, 5 = angry)
last_hit_pos = (0, 0)
last_tap_time = 0
touch_start_time = 0
last_touch_on_time = 0
hit_anim_timeout = 0
tickle_anim_timeout = 0
last_talk_update = time.time()

def lerp(start, end, t):
    return start + t * (end - start)

def set_emotion_targets(emotion):
    global base_eye_h, target_eye_x, target_mouth_w, target_mouth_h, target_eye_pos_x
    target_eye_pos_x = 240.0
    if emotion == "idle":
        base_eye_h, target_eye_x, target_mouth_w, target_mouth_h = 60.0, 100.0, 80.0, 20.0
    elif emotion == "happy":
        base_eye_h, target_eye_x, target_mouth_w, target_mouth_h = 35.0, 110.0, 120.0, 60.0
    elif emotion == "sad":
        base_eye_h, target_eye_x, target_mouth_w, target_mouth_h = 40.0, 90.0, 80.0, 35.0
    elif emotion == "angry":
        base_eye_h, target_eye_x, target_mouth_w, target_mouth_h = 25.0, 120.0, 130.0, 40.0
    elif emotion == "talk":
        base_eye_h, target_eye_x, target_mouth_w, target_mouth_h = 60.0, 100.0, 120.0, 40.0

def run_startup():
    global target_eye_h, target_eye_pos_x, target_mouth_w, target_mouth_h, current_emotion
    time.sleep(1)
    target_eye_h = 60.0
    target_mouth_w, target_mouth_h = 80.0, 20.0
    time.sleep(1.5)
    target_eye_pos_x = 180.0
    time.sleep(0.8)
    target_eye_pos_x = 300.0
    time.sleep(0.8)
    target_eye_pos_x = 240.0
    time.sleep(0.5)
    current_emotion = "idle"
    set_emotion_targets("idle")

startup_thread = threading.Thread(target=run_startup, daemon=True)
startup_thread.start()

def terminal_input():
    global current_emotion, saved_emotion, running, hit_taps, hit_cycle_count
    print("\n--- Bitty Control Terminal ---")
    while running:
        try:
            cmd = input("Command: ").lower().strip()
            if cmd in ["idle", "happy", "sad", "talk", "angry"]:
                current_emotion = saved_emotion = cmd
                hit_taps = 0
                hit_cycle_count = 0 # Maafin kalau diset manual
                set_emotion_targets(cmd)
            elif cmd == "exit": running = False
        except EOFError: break

input_thread = threading.Thread(target=terminal_input, daemon=True)
input_thread.start()

stop_voice = threading.Event()

def run_voice_assistant():
    global current_emotion, saved_emotion, running
    print("[Voice] Initializing Ears...")
    ears = Ears(wake_word_threshold=0.6)
    
    print("[Voice] Ready! Say 'Hey Jarvis'")
    while running and not stop_voice.is_set():
        try:
            # 1. Listen for Wake Word
            if ears.listen_for_wake_word(stop_voice):
                if stop_voice.is_set(): break
                print("[Voice] Wake word detected!")
                
                # Visual Feedback: Listening
                saved_emotion = current_emotion # Backup
                current_emotion = "happy" 
                set_emotion_targets("happy")

                # 2. Record Command
                audio_path = ears.record_command(duration=5)
                
                if audio_path:
                    # Visual Feedback: Thinking
                    current_emotion = "idle" # Neutral expression while thinking
                    set_emotion_targets("idle")
                    
                    # 3. Transcribe
                    user_text = brain.transcribe_audio(audio_path)
                    print(f"[Voice] User: {user_text}")
                    
                    if user_text:
                        # 4. Get LLM Response
                        remote = get_remote_metrics()
                        local = get_local_metrics()
                        response_text, _ = brain.get_bitty_response("voice_user", user_text, remote, local)
                        print(f"[Voice] Bitty: {response_text}")
                        
                        # 5. TTS & Speak
                        current_emotion = "talk"
                        set_emotion_targets("talk")
                        
                        outfile = "response.mp3"
                        asyncio.run(brain.speak_response(response_text, outfile))
                        
                        pygame.mixer.music.load(outfile)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and not stop_voice.is_set():
                            time.sleep(0.1)
                            
                        # Return to normal
                        current_emotion = saved_emotion
                        set_emotion_targets(saved_emotion)
                    
        except Exception as e:
            print(f"[Voice] Error: {e}")
            time.sleep(1)
            
    ears.close()

voice_thread = threading.Thread(target=run_voice_assistant, daemon=True)
voice_thread.start()

last_blink = time.time()
is_blinking = False

try:
    while running:
        screen.fill(BLACK)
        now = time.time()
        
        mouse_pressed = pygame.mouse.get_pressed()[0]
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pressed:
            if last_touch_on_time == 0 or (now - last_touch_on_time) > JITTER_GRACE:
                touch_start_time = now
            last_touch_on_time = now
        
        is_effectively_touching = (now - last_touch_on_time) < JITTER_GRACE

        # A. Update Animasi Timeout
        if now < hit_anim_timeout:
            current_emotion = "hit"
            base_eye_h = target_eye_h = 2.0
            target_mouth_h, target_mouth_w = 15.0, 60.0
        elif now < tickle_anim_timeout:
            current_emotion = "tickle"
            base_eye_h = 5.0 
            target_mouth_h, target_mouth_w = 50.0, 140.0
            target_offset_y = random.uniform(-6, 6)
        elif current_emotion != "startup":
            if current_emotion in ["hit", "tickle"]:
                current_emotion = saved_emotion
                set_emotion_targets(saved_emotion)
                target_offset_y = 0

            # B. Logic TICKLE (Hold)
            if is_effectively_touching and (now - touch_start_time) > HOLD_THRESHOLD:
                if hit_taps < 2: 
                    saved_emotion = "idle" # Kelitikan bikin Bitty luluh jadi idle
                    tickle_anim_timeout = now + 1.2

        if current_emotion not in ["startup", "hit", "tickle"]:
            if not is_blinking:
                target_eye_h = base_eye_h
                if now - last_blink > random.uniform(3, 7):
                    is_blinking, last_blink = True, now
            else:
                target_eye_h = 2.0
                if now - last_blink > 0.15:
                    is_blinking, last_blink = False, now

        if current_emotion == "talk" and now - last_talk_update > 0.15:
            target_mouth_h, target_mouth_w = float(random.randint(40, 90)), float(random.randint(100, 160))
            last_talk_update = now

        curr_eye_h = lerp(curr_eye_h, target_eye_h, 0.15)
        curr_eye_x = lerp(curr_eye_x, target_eye_x, 0.15)
        curr_eye_pos_x = lerp(curr_eye_pos_x, target_eye_pos_x, 0.1)
        curr_mouth_w = lerp(curr_mouth_w, target_mouth_w, 0.15)
        curr_mouth_h = lerp(curr_mouth_h, target_mouth_h, 0.15)
        curr_offset_y = lerp(curr_offset_y, target_offset_y, 0.3)

        e_h, e_x, e_pos_x = int(curr_eye_h), int(curr_eye_x), int(curr_eye_pos_x)
        m_w, m_h, off_y = int(curr_mouth_w), int(curr_mouth_h), int(curr_offset_y)
        
        eye_color = WHITE if current_emotion != "angry" else RED
        pygame.draw.ellipse(screen, eye_color, (e_pos_x - e_x - 40, 120 - (e_h//2) + off_y, 80, e_h))
        pygame.draw.ellipse(screen, eye_color, (e_pos_x + e_x - 40, 120 - (e_h//2) + off_y, 80, e_h))

        if m_w > 20 and m_h > 12: 
            mouth_rect = pygame.Rect(e_pos_x - (m_w//2), 200 + off_y, m_w, m_h)
            if current_emotion in ["sad", "hit", "angry"]: 
                pygame.draw.arc(screen, eye_color, mouth_rect, 0, math.pi, 6)
            elif current_emotion in ["happy", "tickle"]: 
                pygame.draw.arc(screen, eye_color, mouth_rect, math.pi, 0, 8)
            elif current_emotion == "talk": 
                pygame.draw.ellipse(screen, eye_color, (e_pos_x - (m_w//2), 220 - (m_h//4) + off_y, m_w, m_h), 4)
            else: 
                pygame.draw.arc(screen, eye_color, mouth_rect, math.pi, 0, 4)

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                dist = math.hypot(event.pos[0] - last_hit_pos[0], event.pos[1] - last_hit_pos[1])
                
                # Logic Triple Tap (Pukul)
                if (now - last_tap_time < HIT_WINDOW) and (dist < HIT_RADIUS):
                    hit_taps += 1
                else:
                    hit_taps = 1
                    last_hit_pos = event.pos
                last_tap_time = now
                
                if hit_taps >= 3:
                    hit_taps = 0
                    hit_cycle_count += 1
                    hit_anim_timeout, curr_offset_y = now + 0.6, 60
                    
                    # Logic Akumulasi Pukulan
                    if hit_cycle_count == 3: # Total 9 kali pukul
                        current_emotion = saved_emotion = "sad"
                        set_emotion_targets("sad")
                    elif hit_cycle_count >= 5: # Total 15 kali pukul
                        current_emotion = saved_emotion = "angry"
                        set_emotion_targets("angry")

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

        pygame.display.flip()
        clock.tick(60)

except KeyboardInterrupt: 
    running = False
    stop_voice.set()
finally: 
    stop_voice.set()
    pygame.quit()
