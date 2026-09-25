import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from gtts import gTTS
from livekit import api
from livekit.api import AccessToken, VideoGrants

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    groq_api_key=os.getenv("GROQ_API_KEY"),
)

def make_token(room: str = "voice-room-1", name: str = "user1"):
    token = AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    ).with_identity(name).with_grants(
        VideoGrants(room_join=True, room=room)
    ).to_jwt()
    return token

def speak(text: str, out: str = "out.mp3"):
    gTTS(text=text, lang="en").save(out)
    return out

if __name__ == "__main__":
    print("LLM test:", llm.invoke("Say ok in 3 words").content[:100])
    print(speak("Voice line working"))
    print("TTS done: out.mp3")


def make_token(room: str = "voice-room-1", name: str = "user1"):
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    ).with_identity(name).with_grants(
        api.VideoGrants(room_join=True, room=room)
    ).to_jwt()
    return token

if __name__ == "__main__":
    import asyncio
    print("LLM test:", llm.invoke("Say ok in 3 words").content[:100])
    print(speak("Voice line working"))
    print("TTS done: out.mp3")
    print("TOKEN len:", len(make_token()))