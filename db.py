import psycopg2
import pprint
import moviepy.editor as mp

METADATA = {
    "EP_DATE": None,
    "TIME_LENGTH": None,
    "DESCRIPTION": None,
    "TEXT": None,
    "TEXT_LENGTH": None,
    "KEYWORDS": None,
    "SEMANTICS": None,
    }

def video_to_audo():
    video_file = input("Please enter path to video: ")
    clip = mp.VideoFileClip(video_file)
    audio_file = input("Please enter where you'd like to store audio: ")
    clip.audio.write_audiofile(audio_file)

def transcribe():
    audo_file = input("Please enter path to audio file: ")
    model = whisper.load_model("small")
    print(f"Transcribing. This may take a while...")
    result = model.transcribe(audo_file)
    text = result["text"]
    prefix = audo_file.split(".")
    text_file = prefix[0] + ".txt"
    with open(text_file, "w+") as f:
        f.write(text)
    print(f"Saved transcript to {text_file}")
    return text

def gen_insert_cmd(text: str):
    metadata = {}
    for key in METADATA.keys():
        if key == "TEXT_LENGTH":
            metadata[key] = len(text)
        elif key == "TEXT":
            metadata[key] = text
        else:
            metadata[key] = scrub_input(input(f"Please enter {key}: "))
    return (
        "INSERT INTO catalog (EP_DATE, TIME_LENGTH, DESCRIPTION, TEXT, TEXT_LENGTH, "
        + f"KEYWORDS, SEMANTICS) VALUES ('{metadata['EP_DATE']}', "
        + f"'{metadata['TIME_LENGTH']}', '{metadata['DESCRIPTION']}', "
        + f"'{metadata['TEXT']}', {metadata['TEXT_LENGTH']}, "
        + f"'{metadata['KEYWORDS']}', '{metadata['SEMANTICS']}') returning "
        + "EP_DATE, TIME_LENGTH, DESCRIPTION"
            )

def exec_db_command(conn, cmd: str):
    cursor = conn.cursor()
    cursor.execute(cmd)
    pprint.pprint(cursor.fetchall())

def scrub_input(text: str):
    return text.replace("'", "")

if __name__ == "__main__":
    transcript = transcribe()
    print("Generating insert command")
    insert_cmd = gen_insert_cmd(scrub_input(transcript))
    print(insert_cmd)
    print("Connecting to database")
    conn = psycopg2.connect(database="podcast-index",
                            host="0.0.0.0",
                            user="ben",
                            password="",
                            port="3892")
    print("Executing insert command")
    exec_db_command(conn=conn, cmd=insert_cmd)
    print("Disconnecting from database")
    conn.close()

