import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from gtts import gTTS

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    groq_api_key=os.getenv("GROQ_API_KEY"),
)

def speak(text: str, out: str = "out.mp3"):
    gTTS(text=text, lang="en").save(out)
    return out

if __name__ == "__main__":
    print("LLM test:", llm.invoke("Say ok in 3 words").content[:100])
    print(speak("Voice line working"))
    print("TTS done: out.mp3")