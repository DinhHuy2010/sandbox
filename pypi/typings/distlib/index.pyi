from _typeshed import Incomplete

from distlib.metadata import Metadata

DEFAULT_INDEX: str
DEFAULT_REALM: str

class PackageIndex:
    boundary: bytes
    url: str | None
    password_handler: Incomplete | None
    ssl_verifier: Incomplete | None
    gpg: Incomplete | None
    gpg_home: Incomplete | None
    def __init__(self, url: str | None = None) -> None: ...
    username: Incomplete | None
    password: Incomplete | None
    realm: Incomplete | None
    def read_configuration(self) -> None: ...
    def save_configuration(self) -> None: ...
    def check_credentials(self) -> None: ...
    def register(self, metadata: Metadata) -> None: ...
    def get_sign_command(
        self,
        filename: Incomplete,
        signer: Incomplete,
        sign_password: Incomplete,
        keystore: Incomplete = None,
    ) -> list[str]: ...
    def run_command(
        self, cmd: list[str], input_data: bytes | None = None
    ) -> tuple[int, bytes, bytes]: ...
    def sign_file(
        self,
        filename: Incomplete,
        signer: Incomplete,
        sign_password: Incomplete,
        keystore: Incomplete = None,
    ) -> Incomplete: ...
    def upload_file(
        self,
        metadata: Metadata,
        filename: str,
        signer: Incomplete = None,
        sign_password: Incomplete = None,
        filetype: str = "sdist",
        pyversion: str = "source",
        keystore: Incomplete = None,
    ) -> Incomplete: ...
    def upload_documentation(self, metadata: Metadata, doc_dir: str) -> None: ...
    def get_verify_command(self, signature_filename: str, data_filename: str, keystore: Incomplete = None) -> list[str]: ...
    def verify_signature(self, signature_filename: str, data_filename: str, keystore: Incomplete = None) -> bool: ...
    def download_file(self, url: str, destfile: str, digest: Incomplete = None, reporthook: Incomplete = None) -> None: ...
    def send_request(self, req: Incomplete) -> Incomplete: ...
    def encode_request(self, fields: Incomplete, files: Incomplete) -> Incomplete: ...
    def search(self, terms: Incomplete, operator: Incomplete = None) -> Incomplete: ...
