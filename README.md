
# **SQL with Gen AI**
**Objectives**
- Automate SQL query generation for efficient data retrieval, manipulation, and visualization
- Enhance insights by integrating data from PDFs and CSVs

# **Environment Setup**

Follow these steps to set up the environment for the **SQL With GenAI** project.

## Prerequisites

- Python 3.8+ installed

### 1. Clone the Repository

```bash
git clone https://github.com/nishanthdass/csv-summarizer.git
```

### 2. Navigate to the Main Directory
```bash
cd csv-summarizer
```

### 3. Create a Virtual Environment
Create a new virtual environment
```bash
python -m venv venv
```

### 4. Activate the Virtual Environment
Activate the newly created environment:
```bash
.\venv\Scripts\Activate.ps1
```

### 5. Install the Required Dependencies
Install the project dependencies listed in the requirements.txt
```bash
pip install -r requirements.txt
```

### 6. Create a .env File
In the project’s root directory, create a .env file with the following keys:

POSTGRES_USER=\
POSTGRES_PASSWORD=\
POSTGRES_DB= &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # database name\
POSTGRES_HOST=\
POSTGRES_PORT=

OPENAI_API_VERSION="2024-05-01-preview"\
OPENAI_MODEL_NAME="gpt-4-turbo-preview"\
OPENAI_EMB_MODEL="text-embedding-3-large"\
OPENAI_EMB_MODEL_SMALL="text-embedding-3-small"\
OPENAI_API_KEY=\
OPENAI_BASE_URL="https://api.openai.com/v1/"

LANGCHAIN_API_KEY=\
LANGCHAIN_TRACING_V2=true

NEO4J_URI= &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; # e.g., "neo4j+s://your-instance.databases.neo4j.io"\
NEO4J_USERNAME=\
NEO4J_PASSWORD=\
NEO4J_DATABASE=

# **Starting the backend server**
Follow these steps to start the FastAPI server

### 1. Navigate to the Main Directory
```bash
cd csv-summarizer
```

### 2. Activate the Virtual Environment
Activate the virtual environment:
```bash
.\venv\Scripts\Activate.ps1
```

### 3. Navigate to the Backend Directory
```bash
cd backend
```

### 4. Start the FastAPI Server
```bash
uvicorn main:app --reload
```

# **Starting the frontend server**
Follow these steps to start the React UI

## Prerequisites

- Node.js and npm installed

### 1. Navigate to the Frontend Directory
```bash
cd csv-summarizer\frontend
```

### 2. Install the frontend dependencies
```bash
npm install
```

### 3. Start the frontend development server
```bash
npm start
```
