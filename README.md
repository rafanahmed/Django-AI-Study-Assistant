
# AI Study Assistant (Django Project)

This project is a Django-based web application designed to assist users with studying, featuring AI integration powered by Google Gemini for interactive feedback.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Python 3.x:** Download from [python.org](https://www.python.org/)
* **Git:** Download from [git-scm.com](https://git-scm.com/)
* **Pip:** Usually comes with Python. Ensure it's up to date (`pip install --upgrade pip`).

## Setup Instructions

Follow these steps to get the project running on your local machine:

**1. Clone the Repository:**

Open your terminal or command prompt and clone the project repository:

```bash
git clone <your-repository-url>
cd <repository-directory-name>
```

(Replace `<your-repository-url>` with the actual URL of your Git repository and `<repository-directory-name>` with the name of the folder created by cloning.)

**2. Create a Virtual Environment:**

It’s crucial to use a virtual environment to manage project dependencies separately. We’ll use Python’s built-in `venv` module. Let’s name the environment `genai-env` (as used during development).

Navigate into your project directory (the one containing `manage.py`) in your terminal and run:

```bash
python -m venv genai-env
```

- This command creates a directory named `genai-env` containing a private copy of Python and pip specific to this project.

**3. Activate the Virtual Environment:**

Before installing packages or running the app, you must activate the environment:

- **On macOS / Linux:**

    ```bash
    source genai-env/bin/activate
    ```

- **On Windows (Command Prompt / PowerShell):**

    ```bash
    .\genai-env\Scripts\activate
    ```

Your terminal prompt should now change, usually showing `(genai-env)` at the beginning, indicating the environment is active. You need to activate it every time you open a new terminal to work on this project.

**4. Install Dependencies:**

Install the required Python packages using pip. The essential packages are Django, the Google Generative AI client, and python-dotenv.

```bash
pip install django google-generativeai python-dotenv
```

> **Optional Best Practice:** For easier dependency management, especially in teams, create a `requirements.txt` file listing the dependencies:
> 
> ```
> # requirements.txt
> django>=4.0,<5.0  # Use appropriate version constraints
> google-generativeai
> python-dotenv
> ```
> 
> Then install using: `pip install -r requirements.txt`

**5. Create the `.env` File:**

This file stores your secret API key.

- In the root directory of the project (the same level as `manage.py`), create a file named **`.env`**.
- Open the `.env` file and add your Google Gemini API key:

```env
GOOGLE_API_KEY=YOUR_ACTUAL_API_KEY_HERE
```

- **Important:** Replace `YOUR_ACTUAL_API_KEY_HERE` with the real API key you obtained from [Google AI Studio](https://makersuite.google.com/) or Google Cloud Platform.
- Make sure `.env` is listed in your `.gitignore` file to prevent committing secrets.

**6. Apply Database Migrations:**

Run the initial database setup for Django’s built-in models and any models in your `base` app:

```bash
python manage.py migrate
```

**7. Run the Development Server:**

Start the Django development server:

```bash
python manage.py runserver
```

---

## Accessing the Application

Once the server is running, you can access the application by opening your web browser and navigating to:

```
http://127.0.0.1:8000/
```

The placeholder category pages are available at `/online-tutorials/`, `/study-guides/`, and `/books-articles/`.

The AI endpoint is available at:

```
http://127.0.0.1:8000/api/ai-assistant/
```

(accepting POST requests with JSON)

---

## Key Dependencies

- **Django:** The web framework used for the project.
- **google-generativeai:** The official Google client library for interacting with the Gemini API.
- **python-dotenv:** Used to load environment variables (like API keys) from a `.env` file during development.



