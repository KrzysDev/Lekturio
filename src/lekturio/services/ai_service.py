import os
import sys
from ollama import chat

from ollama import ChatResponse

class AiService:
    def __init__(
        self,
        model: str = "SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M",
    ):
        self.model = model

    def ask(self, prompt: str):
        response: ChatResponse = chat(model=self.model, messages=[
        {
            'role': 'user',
            'content': prompt,
        },
        ])
        return response.message.content


if __name__ == "__main__":
    ai_service = AiService()

    print(ai_service.ask("dlaczego niebo jest niebieskie?"))

    

