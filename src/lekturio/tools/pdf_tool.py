
import textract
text = textract.process(r"C:\Users\USER\Desktop\Sofokles - Antygona.pdf").decode()

print(text)