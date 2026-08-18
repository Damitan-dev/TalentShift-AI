from storage import SessionRepo
# Import the repository that knows how to save and load Session objects.


repo = SessionRepo()
# Create the repository.
# By default, it will look inside the data/ folder.


session_id = "20c501aa-10e8-4eca-82cd-17d53fc1ccac"
# Use the ID from the JSON file you just created.
# Do NOT include ".json" because SessionRepo.load() adds that itself.


loaded_session = repo.load(session_id)
# Read data/<session-id>.json.
# SessionRepo.load() then uses Pydantic to validate the JSON
# and convert it back into a real Session object.


print(loaded_session)
# Print the loaded interview so we can inspect the data.


print(type(loaded_session))
# Prove that Pydantic returned a Session object,
# not just a normal Python dictionary.


print(loaded_session.language)
# Test that we can access Session attributes normally.


print(loaded_session.transcript[0].speaker)
# Test that the nested transcript was also rebuilt
# into proper TranscriptTurn objects.


print(loaded_session.transcript[0].text)
# Show the text from the first saved transcript turn.