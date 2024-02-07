import requests
import logging
import os
import uuid
import progressbar
import shutil
import moviepy.editor as mp
from pydub import AudioSegment
import subprocess
import json


VALID_DOWNLOAD_CONTENT_TYPES = {
    "audio/mpeg": ".mp3",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
}
MINUTES = 5
TIMEOUT = MINUTES * 60
CHUNK_SIZE = 2 * 1024 * 1024
LOG_LEVEL = "INFO"
DOWNLOAD_DIR = "/Users/benrichey/Downloads"
DATA_DIR = "/Users/benrichey/src/podinator/data"
WHISPER_MODEL = "large-v3"

progressbar.streams.wrap_stderr()
progressbar.streams.wrap_stdout()
logging.basicConfig()


class Podinator:
    """
    Podinator

    A one-stop-shop class for handling all the wonderful features Podinator
    has. This includes starting the web server for serving the front-end web UI, and
    handling any/all requests that come from that web UI including:
        - downloading podcast content
        - converting podcast content into .wav format (as required by whisper.cpp)
        - transcribing the podcast content
        - generating a searchable index of the content
        - handling search queries for a podcast
    """

    def __init__(self,):
        self.LOG = logging.getLogger(f"{self.__class__.__name__}")
        self.LOG.setLevel(LOG_LEVEL)
        self.valid_download_content_types = VALID_DOWNLOAD_CONTENT_TYPES
        self.timeout = TIMEOUT
        self.chunk_size = CHUNK_SIZE
        self.download_dir = DOWNLOAD_DIR
        self.data_dir = DATA_DIR
        self.audio_dir = os.path.join(self.data_dir, "audio")
        self.transcript_dir = os.path.join(self.data_dir, "transcripts")
        self.whisper_path = os.path.join(os.getcwd(), "whisper.cpp")
        self.whisper_model = WHISPER_MODEL
        try:
            if not os.path.exists(self.download_dir):
                os.mkdir(self.download_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
            if not os.path.exists(self.audio_dir):
                os.mkdir(self.audio_dir)
            if not os.path.exists(self.transcript_dir):
                os.mkdir(self.transcript_dir)
        except FileNotFoundError as err:
            self.LOG.error(
                f"Failed to initialize local files. Cannot function properly.\n{err}"
            )
            exit(-1)
        self.setup_whisper()

    def convert_to_wav(self, filepath: str) -> str:
        """
        Given a path to a file that is one of the valid file formats, convert it to
        .wav format (as required by whisper.cpp). NOTE: this won't work if the file
        isn't a valid format.
        @param filepath: path to podcast content
        @return: path to .wav file if success, empty string on failure
        """
        if not os.path.exists(filepath):
            self.LOG.error(
                f"Failed to convert {filepath} to .wav format. "
                + "File does not exist."
            )
            return ""
        extension = os.path.splitext(filepath)[1]
        if extension not in self.valid_download_content_types.values():
            self.LOG.error(
                f"Failed to convert {filepath} to .wav format. Invalid extension type: "
                + f"'{extension}'. Expected one of: "
                + f"{self.valid_download_content_types.values()}"
            )
            return ""
        if extension == ".wav":
            return self.wav_to_wav(filepath=filepath)
        elif extension == ".mp4":
            return self.mp4_to_wav(filepath=filepath)
        else:
            return self.mp3_to_wav(filepath=filepath)

    def wav_to_wav(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        shutil.copy(filepath, os.path.join(self.audio_dir, filename))
        return os.path.join(self.audio_dir, filename)

    def mp4_to_wav(self, filepath: str) -> str:
        filename = os.path.splitext(os.path.basename(filepath))[0] + ".wav"
        with mp.VideoFileClip(filepath) as clip:
            clip.audio.write_audiofile(os.path.join(self.audio_dir, filename))
        return os.path.join(self.audio_dir, filename)

    def mp3_to_wav(self, filepath: str) -> str:
        audio = AudioSegment.from_mp3(filepath)
        audio = audio.set_frame_rate(16000)
        filename = os.path.splitext(os.path.basename(filepath))[0] + ".wav"
        audio.export(os.path.join(self.audio_dir, filename), format="wav")
        return os.path.join(self.audio_dir, filename)

    def download_podcast_from_url(self, url: str) -> str:
        """
        Given a URL, try to download the podcast content. Only .mp4/.mp3/.wav
        files will be accepted.

        @param url: URL to download podcast content from
        @return: Upon success, the path to where the content was stored is
        returned. Upon failure, an empty string is returned.
        """
        cleanup = False
        filename = str(uuid.uuid4())
        try:
            return self._unsafe_download_url(url=url, filename=filename)
        except requests.exceptions.Timeout:
            cleanup = True
            self.LOG.error(f"Failed to fetch: {url}\nThe request timed out.")
        except requests.exceptions.ConnectionError as err:
            cleanup = True
            self.LOG.error(f"Failed to fetch: {url}\nThere was a connection error.")
            self.LOG.error(err)
        except requests.exceptions.HTTPError as err:
            cleanup = True
            self.LOG.error(f"Failed to fetch: {url}\nThere was an HTTP error.")
            self.LOG.error(err)
        except Exception as err:
            cleanup = True
            self.LOG.error(f"Failed to fetch: {url}\nAn unknown error occurred.")
            self.LOG.error(err)
        if cleanup:
            ls = os.listdir(self.download_dir)
            fnames = [os.path.splitext(os.path.basename(f))[0] for f in ls]
            if filename in fnames:
                os.remove(os.path.join(self.download_dir, ls[fnames.index(filename)]))

    def _unsafe_download_url(self, url: str, filename: str) -> str:
        response = requests.get(url, stream=True, timeout=self.timeout)
        extension = self.check_content_type(response.headers["Content-Type"])
        filename += extension
        if not extension:
            self.LOG.error(
                "Invalid content type. Acceptable types are: "
                + f"{self.valid_download_content_types}\nReceived: "
                + f"{response.headers['Content-Type']}"
            )
            return ""
        progress_bar = self.new_progressbar(
            max_val=int(response.headers["Content-Length"])
        )
        data_written = 0
        with open(os.path.join(self.download_dir, filename), "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                data_written += self.chunk_size
                if data_written > int(response.headers["Content-Length"]):
                    data_written = int(response.headers["Content-Length"])
                progress_bar.update(data_written)
        progress_bar.finish()
        self.LOG.info(
            f"File from {url} downloaded to "
            + f"{os.path.join(self.download_dir, filename)}"
        )
        return os.path.join(self.download_dir, filename)

    def check_content_type(self, type: str) -> str:
        """
        Given an HTTP Content Type header value, determine if it's valid or not.
        @param type: HTTP Content Type header value
        @return: file extension string if valid, empty string if not
        """
        if type in self.valid_download_content_types.keys():
            return self.valid_download_content_types[type]
        else:
            return ""

    def new_progressbar(self, max_val: int) -> progressbar.ProgressBar:
        widgets = [progressbar.Bar('*'), ' (',
                   progressbar.ETA(), ') ',
                   ]
        bar = progressbar.ProgressBar(maxval=max_val,
                                      widgets=widgets).start()
        return bar

    def transcribe(self, wav_file_path: str) -> str:
        """
        Use pre-compiled whisper.cpp executable to transcribe .wav file into timestamped
        JSON file and store it in the transcript directory.
        @param wav_file_path: path to .wav file
        @return: timestamped transcript in JSON format
        """
        filename = os.path.splitext(os.path.basename(wav_file_path))[0]
        json_file = os.path.join(self.transcript_dir, filename)
        cmd_str = (
            "./whisper.cpp/main --model "
            + f"./whisper.cpp/models/ggml-{self.whisper_model}.bin "
            + f"-f {wav_file_path} --output-file {json_file} --output-json"
        )
        self.LOG.info(cmd_str)
        subprocess.run(cmd_str, shell=True)
        self.LOG.info(f"Saved transcript to {json_file}.json")
        with open(json_file + ".json", "r") as f:
            text = json.load(f)
        return text

    def check_for_whisper_cpp_main(self,) -> bool:
        if not os.path.exists(os.path.join(self.whisper_path, "main")):
            self.LOG.info(
                "whisper.cpp main executable not found at: "
                + f"{os.path.join(self.whisper_path, 'main')}. Building. "
                + "This may take a while."
            )
            return False
        self.LOG.info("whisper.cpp main executable found.")
        return True

    def check_for_whisper_cpp_init(self,) -> bool:
        whisper_cpp_makefile = os.path.join(self.whisper_path, "Makefile")
        if not os.path.exists(whisper_cpp_makefile):
            self.LOG.info(
                "whisper.cpp submodule not found at: "
                + f"{os.path.join(os.getcwd(), 'whisper.cpp')}. Initializing."
            )
            return False
        self.LOG.info("whisper.cpp submodule is initialized.")
        return True

    def check_for_whisper_model(self,) -> bool:
        whisper_model_path = os.path.join(
            os.path.join(self.whisper_path, "models"),
            "ggml-" + self.whisper_model + ".bin"
        )
        if not os.path.exists(whisper_model_path):
            self.LOG.info(
                f"whisper model: '{whisper_model_path}' not found. "
                + "Downloading. This may take a while."
            )
            return False
        self.LOG.info("whisper model found.")
        return True

    def init_whisper_cpp(self,):
        cmd_str = "git submodule update --init --recursive"
        self.LOG.info(cmd_str)
        ret = subprocess.run(cmd_str, shell=True)
        if ret.returncode != 0 or not self.check_for_whisper_cpp_init():
            self.LOG.error(
                "An error occurred when trying to initialize whisper.cpp. "
                + "Cannot recover. Exiting."
            )
            exit(-1)
        self.LOG.info("whisper.cpp submodule initialized.")

    def download_whisper_model(self,):
        download_script = os.path.join(
            os.path.join(self.whisper_path, "models"),
            "download-ggml-model.sh"
        )
        cmd_str = f"bash {download_script} {self.whisper_model}"
        self.LOG.info(cmd_str)
        ret = subprocess.run(cmd_str, shell=True)
        if ret.returncode != 0 or not self.check_for_whisper_model():
            self.LOG.error(
                "An error occurred when trying to download whisper model: "
                + f"{self.whisper_model}. Cannot recover. Exiting."
            )
            exit(-1)
        self.LOG.info("Successfully downloaded whisper model.")

    def build_whisper_cpp_main(self,):
        cmd_str = f"cd {self.whisper_path} && make"
        self.LOG.info(cmd_str)
        ret = subprocess.run(cmd_str, shell=True)
        if ret.returncode != 0 or not self.check_for_whisper_cpp_main():
            self.LOG.error(
                "Failed to build whisper.cpp main executable. Cannot recover. Exiting."
            )
            exit(-1)
        self.LOG.info("Successfully built whisper.cpp main executable.")

    def setup_whisper(self,):
        if not self.check_for_whisper_cpp_init():
            self.init_whisper_cpp()
        if not self.check_for_whisper_model():
            self.download_whisper_model()
        if not self.check_for_whisper_cpp_main():
            self.build_whisper_cpp_main()


if __name__ == "__main__":
    podinator = Podinator()
    filename = podinator.download_podcast_from_url(
        url="https://audioboom.com/posts/8396915-173-the-band-is-back-together.mp3?download=1"
    )
    podinator.convert_to_wav(filepath=filename)
    filepath = podinator.convert_to_wav(filepath=filename)
    podinator.transcribe(wav_file_path=filepath)

