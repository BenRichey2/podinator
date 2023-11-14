import requests
import logging
import os
import uuid
import progressbar
import shutil
import moviepy.editor as mp
from pydub import AudioSegment


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


if __name__ == "__main__":
    podinator = Podinator()
    filename = podinator.download_podcast_from_url(
        url="https://audioboom.com/posts/8396915-173-the-band-is-back-together.mp3?download=1"
    )
    podinator.convert_to_wav(filepath=filename)

