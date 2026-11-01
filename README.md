# StudyFlow 📚

**A simple Python-based study management application designed to help students organize their learning.**

## About the Project

StudyFlow is a personal project developed as part of Harvard's CS50P – Introduction to Programming with Python.

The idea behind StudyFlow is simple: students often struggle to decide what to study, organize their subjects, and maintain a consistent study routine.

StudyFlow aims to make studying more organized by bringing important study-management tools together in one application.

The project is being developed using Python, with JSON for data storage.

## Current Features

- **Add Subjects:** Add new subjects to your personal study list.
- **View Subjects:** Display the subjects you have added.
- **Data Storage:** Save subject information locally using JSON.
- **Input Validation:** Prevent empty or duplicate subject names.

*More features are planned as development continues.*

## Technologies Used

- Python
- JSON
- pytest
- Git and GitHub

## Project Structure

```text
StudyFlow/
│
├── project.py          # Main application
├── test_project.py     # Automated tests
├── requirements.txt    # Project dependencies
├── README.md           # Project documentation
└── .gitignore          # Files excluded from Git
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/yadhavibhattarai-prog/Study--Flow.git
```

### 2. Navigate into the project folder

```bash
cd Study--Flow
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
```

### 4. Activate the virtual environment

For macOS and Linux:

```bash
source .venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

## How to Run StudyFlow

Start the application using:

```bash
python project.py
```

Follow the menu displayed in the terminal to interact with StudyFlow.

## Running Tests

StudyFlow uses pytest for automated testing.

Run the following command:

```bash
pytest -v
```

This runs the available tests and displays their results.

## Future Improvements

The following features are planned for future development:

- Topic and subtopic management
- Study-session tracking
- Daily and weekly study goals
- Revision scheduling
- Examination management
- Study progress tracking and statistics
- Improved user interface

## Project Status

**Currently in development.**

StudyFlow is an independent learning project focused on improving my Python programming, software development, problem-solving, and testing skills.

## Author

Developed as a personal programming project by a Data Science student.

**Course:** CS50P – Introduction to Programming with Python  
**Institution:** Harvard University

---

*StudyFlow — Organize your learning. Focus on your progress.*