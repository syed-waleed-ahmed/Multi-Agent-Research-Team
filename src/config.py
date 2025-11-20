# src/config.py
from __future__ import annotations
import os

from dotenv import load_dotenv
from crewai import LLM
from crewai_tools import SerperDevTool

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in .env")

if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY is not set in .env (required for SerperDevTool).")

# Groq via LiteLLM (CrewAI's LLM wrapper)
llm = LLM(
    model=f"groq/{GROQ_MODEL}",
    temperature=0.2,
    max_tokens=512,   # ⬅️ much smaller than 2048 → fewer tokens per call
)

# Web search tool (Serper)
web_search_tool = SerperDevTool()
