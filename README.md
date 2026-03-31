# 🎤 AI Voice Assistant with Ollama & FastAPI

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-26+-blue.svg)](https://www.docker.com/)

A **local, privacy-first voice assistant** that uses **Ollama (Mistral 7B)** for LLM inference, **speech recognition** for voice input, and **text‑to‑speech** for spoken responses. Features include conversation memory, application control (open/close 1100+ apps), web search, and a REST API for integration.

> Built as a portfolio project for **AI Voice & Language Model Engineer** roles – demonstrates end‑to‑end ASR, LLM fine‑tuning, API design, and containerisation.

---

## ✨ Features

- 🎙️ **Wake word detection** – say *"Assistant"* to activate
- 🧠 **Conversation memory** – maintains context across multiple turns
- 📱 **Voice‑controlled applications** – open/close 1174+ Windows apps
- 🌐 **Web search** – hands‑free Google queries
- 🧩 **REST API** – FastAPI wrapper for programmatic access
- 🐳 **Docker support** – containerised deployment
- 🛡️ **Privacy‑first** – everything runs locally (Ollama + offline STT/TTS)

---

## 🛠️ Tech Stack

| Component          | Technology                                                                 |
|--------------------|----------------------------------------------------------------------------|
| Speech recognition | `speech_recognition` (Google Web Speech API, offline Whisper possible)     |
| Text‑to‑speech     | `pyttsx3` (Windows SAPI)                                                   |
| LLM                | Ollama + `mistral:instruct` (7B parameters)                                |
| API framework      | FastAPI + Uvicorn                                                          |
| Containerisation   | Docker                                                                     |
| App scanning       | Custom Windows registry + shortcut scanner                                 |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running
- Pull the model:  
  ```bash
  ollama pull mistral:instruct