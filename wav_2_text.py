import whisper

def transcribe():
    audo_file = input("Please enter path to audio file: ")
    model = whisper.load_model("small")
    result = model.transcribe(audo_file)
    text = result["text"]
    prefix = audo_file.split(".")
    text_file = prefix[0] + ".txt"
    with open(text_file, "w+") as f:
        f.write(text)

transcribe()

