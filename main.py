"""
PC Vocal Assistant with Ollama Mistral
======================================

Features:
- Wake word "Assistant"
- Voice commands: open/close apps, web search, ask questions
- Conversation memory (context window)
- REST API-ready (FastAPI wrapper optional)
- Docker support

Dependencies:
pip install speech_recognition pyttsx3 pyaudio requests
"""

import speech_recognition as sr
import pyttsx3
import requests
import json
import os
import subprocess
import re
import time
from datetime import datetime

class VocalAssistant:
    def __init__(self, mic_device_index=None):
        # Ollama configuration
        self.ollama_url = "http://127.0.0.1:11434"
        self.model_name = "mistral:instruct"
        self.retries = 2
        self.retry_delay = 2

        # Conversation memory (stores last N exchanges)
        self.conversation_history = []
        self.max_history = 5

        # Speech recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.5
        self.recognizer.phrase_time_limit = None
        self.recognizer.non_speaking_duration = 0.8

        # Microphone selection
        if mic_device_index is None:
            mic_index = self.select_microphone()  # FIXED: only one call
            if mic_index is None:
                print("⚠️ No microphone selected. Voice input disabled.")
                self.microphone = None
            else:
                self.microphone = sr.Microphone(device_index=mic_index)
        else:
            self.microphone = sr.Microphone(device_index=mic_device_index)

        # Text-to-speech
        self.tts_engine = pyttsx3.init()
        self.setup_tts()

        # Assistant state
        self.active = True

        # Action system
        self.setup_action_system()

        print("🤖 Vocal Assistant initialized")
        self.speak("Hello! I am your vocal assistant. Say 'Assistant' to wake me up.")

    # ------------------------------------------------------------------
    # Microphone selection
    # ------------------------------------------------------------------
    def select_microphone(self):
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            input_devices = []
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev['maxInputChannels'] > 0:
                    input_devices.append((i, dev['name']))
            p.terminate()

            if not input_devices:
                print("❌ No input microphone found.")
                return None

            print("\nAvailable input microphones:")
            for idx, (i, name) in enumerate(input_devices):
                print(f"  {idx}: [{i}] {name}")

            choice = input(f"\nSelect microphone (0-{len(input_devices)-1}) or press Enter for default: ").strip()
            if choice.isdigit() and 0 <= int(choice) < len(input_devices):
                return input_devices[int(choice)][0]  # return the actual device index
            return None
        except Exception as e:
            print(f"⚠️ Could not list microphones: {e}")
            return None

    # ------------------------------------------------------------------
    # TTS setup
    # ------------------------------------------------------------------
    def setup_tts(self):
        """Configure text-to-speech (Windows SAPI)."""
        try:
            voices = self.tts_engine.getProperty('voices')
            # Prefer an English voice
            for voice in voices:
                if 'english' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            self.tts_engine.setProperty('rate', 160)
            self.tts_engine.setProperty('volume', 1.0)
            print("✅ Text-to-speech configured")
        except Exception as e:
            print(f"❌ TTS error: {e}")

    def speak(self, text):
        """Speak using pyttsx3."""
        if not text or not text.strip():
            return
        print(f"🔊 Assistant: {text}")
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"❌ TTS failed: {e}")

    # ------------------------------------------------------------------
    # Ollama connection check
    # ------------------------------------------------------------------
    def is_ollama_running(self):
        """Check if Ollama server is reachable."""
        try:
            requests.get(self.ollama_url, timeout=2)
            return True
        except:
            return False

    # ------------------------------------------------------------------
    # Conversation memory
    # ------------------------------------------------------------------
    def add_to_history(self, user_input, assistant_response):
        """Store exchange in memory."""
        self.conversation_history.append({
            "user": user_input,
            "assistant": assistant_response
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

    def build_context_prompt(self, new_prompt):
        """Build prompt with conversation history."""
        context = ""
        for exchange in self.conversation_history[-3:]:  # last 3 exchanges
            context += f"User: {exchange['user']}\nAssistant: {exchange['assistant']}\n"
        return f"{context}User: {new_prompt}\nAssistant:"

    # ------------------------------------------------------------------
    # Mistral API with retry
    # ------------------------------------------------------------------
    def query_mistral(self, prompt, use_history=True):
        """Send query to Ollama, optionally with conversation memory."""
        if not self.is_ollama_running():
            self.speak("Ollama server is not running. Please start it with 'ollama serve'.")
            return None

        full_prompt = self.build_context_prompt(prompt) if use_history else prompt

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.7, "max_tokens": 200}
        }

        for attempt in range(self.retries + 1):
            try:
                print(f"🤖 Sending to Mistral (attempt {attempt+1})...")
                response = requests.post(f"{self.ollama_url}/api/generate",
                                         json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                reply = result.get('response', '').strip()
                if reply:
                    print(f"✅ Response: {reply[:100]}...")
                    if use_history:
                        self.add_to_history(prompt, reply)
                    return reply
                else:
                    print("⚠️ Empty response")
            except requests.exceptions.Timeout:
                print(f"❌ Timeout (attempt {attempt+1})")
            except requests.exceptions.ConnectionError:
                print(f"❌ Connection error (attempt {attempt+1})")
            except Exception as e:
                print(f"❌ API error: {e}")
            if attempt < self.retries:
                time.sleep(self.retry_delay)
        self.speak("Mistral is not responding. Please check your Ollama server.")
        return None

    # ------------------------------------------------------------------
    # Action system (app control, web search, etc.)
    # ------------------------------------------------------------------
    def setup_action_system(self):
        self.action_functions = {
            "open_application": self.action_open_application,
            "close_application": self.action_close_application,
            "list_applications": self.action_list_applications,
            "web_search": self.action_web_search
        }
        self.action_keywords = {
            "open": ["open", "launch", "start", "execute", "run"],
            "close": ["close", "quit", "exit", "stop", "terminate"],
            "list": ["list", "show", "display", "applications"],
            "search": ["search", "find", "google", "bing"]
        }
        self.load_scanned_applications()
        if not hasattr(self, 'applications') or not self.applications:
            self.setup_default_applications()

    def load_scanned_applications(self):
        try:
            app_file = os.path.join(os.path.dirname(__file__), "applications_assistant.json")
            if os.path.exists(app_file):
                with open(app_file, 'r', encoding='utf-8') as f:
                    scanned = json.load(f)
                self.applications = {}
                self.app_commands_map = {}
                for key, data in scanned.items():
                    self.applications[key] = {
                        "name": data["nom"],
                        "path": data["chemin"],
                        "process": data["processus"]
                    }
                    for cmd in data.get("commandes", []):
                        self.app_commands_map[cmd.lower()] = key
                print(f"📱 Loaded {len(self.applications)} applications")
                return True
        except Exception as e:
            print(f"⚠️ Could not load apps: {e}")
        return False

    def setup_default_applications(self):
        print("📱 Using default apps")
        self.applications = {
            "chrome": {"name": "Google Chrome", "path": "chrome", "process": "chrome.exe"},
            "notepad": {"name": "Notepad", "path": "notepad", "process": "notepad.exe"},
            "calculator": {"name": "Calculator", "path": "calc", "process": "calc.exe"}
        }
        self.app_commands_map = {}
        for key, data in self.applications.items():
            self.app_commands_map[key] = key

    def find_application(self, query):
        """Find app by name or command alias."""
        query = query.lower().strip()
        # First check direct command mapping
        if query in self.app_commands_map:
            key = self.app_commands_map[query]
            return key, self.applications[key]
        # Then check if query contains app name
        for key, data in self.applications.items():
            if data["name"].lower() in query or key in query:
                return key, data
        return None, None

    def action_open_application(self, params):
        app_name = params.get("application", "")
        if not app_name:
            return False, "Which application do you want to open?"
        key, data = self.find_application(app_name)
        if not data:
            return False, f"Application '{app_name}' not found."
        try:
            subprocess.Popen(data["path"], shell=True)
            return True, f"Opening {data['name']}."
        except Exception as e:
            return False, f"Could not open {data['name']}: {e}"

    def action_close_application(self, params):
        app_name = params.get("application", "")
        if not app_name:
            return False, "Which application do you want to close?"
        key, data = self.find_application(app_name)
        if not data:
            return False, f"Application '{app_name}' not found."
        try:
            subprocess.run(f'taskkill /F /IM "{data["process"]}"', shell=True)
            return True, f"Closed {data['name']}."
        except:
            return False, f"Could not close {data['name']}."

    def action_list_applications(self, _=None):
        names = list(self.applications.keys())[:10]
        return True, f"I have {len(self.applications)} apps. Examples: {', '.join(names)}."

    def action_web_search(self, params):
        query = params.get("query", "")
        if not query:
            return False, "What do you want to search for?"
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        subprocess.run(f'start "" "{url}"', shell=True)
        return True, f"Searching for {query}."

    def categorize_request(self, command):
        command_lower = command.lower()
        for cat, keywords in self.action_keywords.items():
            if any(kw in command_lower for kw in keywords):
                return "ACTION", cat, command
        return "QUESTION", None, command

    def analyze_action_request(self, command, action_type):
        if action_type == "open":
            # Extract app name (everything after the verb)
            words = command.split()
            for i, w in enumerate(words):
                if w in self.action_keywords["open"]:
                    app = " ".join(words[i+1:])
                    return "open_application", {"application": app}
            return "open_application", {"application": command}
        elif action_type == "close":
            for key in self.applications:
                if key in command.lower():
                    return "close_application", {"application": key}
            return "close_application", {"application": command}
        elif action_type == "list":
            return "list_applications", {}
        elif action_type == "search":
            # Extract query after "search"
            match = re.search(r"search\s+(.+)", command.lower())
            if match:
                return "web_search", {"query": match.group(1)}
            return "web_search", {"query": command}
        return None, None

    def process_command(self, command):
        """Main command processor."""
        cmd_lower = command.lower()
        # Exit commands
        if any(w in cmd_lower for w in ["goodbye", "exit", "quit", "stop assistant"]):
            self.speak("Goodbye!")
            self.active = False
            return
        # Help
        if any(w in cmd_lower for w in ["help", "what can you do"]):
            self.speak("I can open applications, close them, search the web, or answer questions using Mistral.")
            return

        # Categorize
        req_type, action_type, _ = self.categorize_request(command)
        if req_type == "ACTION":
            func_name, params = self.analyze_action_request(command, action_type)
            if func_name and func_name in self.action_functions:
                success, msg = self.action_functions[func_name](params)
                self.speak(msg)
            else:
                self.speak(f"Sorry, I cannot perform '{action_type}' right now.")
        else:  # QUESTION
            self.speak("Let me think...")
            reply = self.query_mistral(command, use_history=True)
            if reply:
                self.speak(reply)
            else:
                self.speak("I could not get an answer.")

    # ------------------------------------------------------------------
    # Wake word and conversation loop
    # ------------------------------------------------------------------
    def listen_for_wake_word(self):
        if self.microphone is None:
            print("❌ No microphone available. Cannot listen for wake word.")
            return  # FIXED: return only after the message, not before the rest

        print("👂 Waiting for wake word 'Assistant'...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        while self.active:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=4)
                text = self.recognizer.recognize_google(audio, language='en-US').lower()
                if 'assistant' in text:
                    self.speak("Here! I'm listening.")
                    self.conversation_mode()
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"Listening error: {e}")
                time.sleep(1)

    def conversation_mode(self):
        if self.microphone is None:
            print("❌ No microphone available. Cannot start conversation.")
            return
        print("💬 Conversation mode active. Say 'done' to stop.")
        while self.active:
            try:
                with self.microphone as source:
                    print("🎤 Speak now...")
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=20)
                command = self.recognizer.recognize_google(audio, language='en-US')
                print(f"🎤 Command: {command}")
                if 'done' in command.lower() or 'finished' in command.lower():
                    self.speak("Conversation ended. Say 'Assistant' to wake me again.")
                    break
                self.process_command(command)
                if not self.active:
                    break
                self.speak("Anything else?")
            except sr.WaitTimeoutError:
                self.speak("I didn't hear anything. Going back to standby.")
                break
            except sr.UnknownValueError:
                self.speak("Sorry, I didn't catch that.")
            except Exception as e:
                print(f"Conversation error: {e}")
                break

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run(self):
        print("🚀 Starting assistant...")
        print("💡 Say 'Assistant' to wake me up.")
        print("💡 Say 'goodbye' to exit.")
        try:
            self.listen_for_wake_word()
        except KeyboardInterrupt:
            print("\n👋 Stopped.")
        finally:
            self.speak("Goodbye!")

def main():
    print("=" * 50)
    print("PC Vocal Assistant with Ollama Mistral")
    print("=" * 50)
    assistant = VocalAssistant()
    assistant.run()

if __name__ == "__main__":
    main()