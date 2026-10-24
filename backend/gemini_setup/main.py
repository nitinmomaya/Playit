# Import create_interaction.
from gemini_setup.service import create_interaction


# Check __name__ == '__main__'.
if __name__ == "__main__":
    # Call print.
    print(create_interaction("Explain how AI works in a few words"))

# File summary
# - Runs a small Gemini demonstration when executed directly.
# - Does not start the FastAPI application.
