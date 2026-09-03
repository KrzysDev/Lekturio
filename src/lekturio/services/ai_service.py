from ollama import chat
# from pathlib import Path

# Pass in the path to the image
path = input('Please enter the path to the image: ')

# You can also pass in base64 encoded image data
# img = base64.b64encode(Path(path).read_bytes()).decode()
# or the raw bytes
# img = Path(path).read_bytes()

response = chat(
  model='medgemma1.5:latest',
  messages=[
    {
      'role': 'user',
      'content': 'Extract the text from the image. Return only what you see in this page of this book. Nothing else. Keep the text formatting the same as it is on the page',
      'images': [path],
    }
  ],
  think=False
)

print(response.message.content)