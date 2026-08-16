# storage.py

from pathlib import Path
# Path gives us a clean way to work with folders and filenames.

from models import Session
# Import our validated Session model.


class SessionRepo:

    def __init__(self, root="data"):
        # Turn the folder name into a Path object.
        self.root = Path(root)

        # Create the data folder if it does not already exist.
        self.root.mkdir(exist_ok=True)


    def save(self, session: Session) -> None:
        # Build a filename using this interview's unique session ID.
        path = self.root / f"{session.id}.json"

        # Convert the Pydantic Session into JSON and save it to disk.
        path.write_text(
            session.model_dump_json(indent=2),
            encoding="utf-8"
        )


    def load(self, session_id: str) -> Session:
        # Find the JSON file belonging to this session.
        path = self.root / f"{session_id}.json"

        # Read the JSON file as text.
        json_text = path.read_text(
            encoding="utf-8"
        )

        # Validate the JSON and turn it back into a Session object.
        return Session.model_validate_json(json_text)