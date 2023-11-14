import requests
import logging
import os
import uuid
import progressbar


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
    podinator.download_podcast_from_url(
        url="https://audioboom.com/posts/8396915-173-the-band-is-back-together.mp3?download=1"
    )

