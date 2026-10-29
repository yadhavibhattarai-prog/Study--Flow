import json
import os
from pathlib import Path
import shutil
import uuid

DATA_FILE = Path("studyflow_data.json")
DATA_COLLECTIONS = ("subjects", "topics", "sessions", "revisions", "exams", "goals")
TOPIC_DIFFICULTIES = ("Easy", "Medium", "Hard")
TOPIC_PRIORITIES = ("Low", "Medium", "High")
TOPIC_STATUSES = ("Not started", "In progress", "Completed")


def create_empty_data():
    return {collection: [] for collection in DATA_COLLECTIONS}


def validate_data(data, allow_missing_subject_ids=False):
    if not isinstance(data, dict):
        raise ValueError("StudyFlow data must be a JSON object.")

    for collection in DATA_COLLECTIONS:
        if collection not in data or not isinstance(data[collection], list):
            raise ValueError(f"StudyFlow data must contain a '{collection}' list.")
        if any(not isinstance(record, dict) for record in data[collection]):
            raise ValueError(f"Every entry in '{collection}' must be an object.")

    subject_ids = set()
    for subject in data["subjects"]:
        name = subject.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every subject must have a non-empty name.")

        subject_id = subject.get("id")
        if allow_missing_subject_ids and (subject_id is None or subject_id == ""):
            continue
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("Every subject must have a non-empty string ID.")
        if subject_id in subject_ids:
            raise ValueError(f"Duplicate subject ID: {subject_id}")
        subject_ids.add(subject_id)

        if "archived" in subject and not isinstance(subject["archived"], bool):
            raise ValueError("A subject's 'archived' value must be a boolean.")

    topic_ids = set()
    topic_names_by_subject = {}
    topics_by_id = {}
    for topic in data["topics"]:
        topic_id = topic.get("id")
        if not isinstance(topic_id, str) or not topic_id.strip():
            raise ValueError("Every topic must have a non-empty string ID.")
        if topic_id in topic_ids:
            raise ValueError(f"Duplicate topic ID: {topic_id}")
        topic_ids.add(topic_id)
        topics_by_id[topic_id] = topic

        name = topic.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every topic must have a non-empty name.")

        subject_id = topic.get("subject_id")
        if subject_id not in subject_ids:
            raise ValueError(f"Topic '{name}' references an unknown subject ID.")
        normalized_name = name.strip().casefold()
        names = topic_names_by_subject.setdefault(subject_id, set())
        if normalized_name in names:
            raise ValueError(f"Duplicate topic name '{name}' in the same subject.")
        names.add(normalized_name)

        if topic.get("difficulty") not in TOPIC_DIFFICULTIES:
            raise ValueError(f"Topic '{name}' has an invalid difficulty.")
        if topic.get("priority") not in TOPIC_PRIORITIES:
            raise ValueError(f"Topic '{name}' has an invalid priority.")
        if topic.get("status") not in TOPIC_STATUSES:
            raise ValueError(f"Topic '{name}' has an invalid completion status.")
        if "archived" in topic and not isinstance(topic["archived"], bool):
            raise ValueError("A topic's 'archived' value must be a boolean.")

    for topic in data["topics"]:
        parent_id = topic.get("parent_id")
        if parent_id is not None:
            parent = topics_by_id.get(parent_id)
            if parent is None or parent["subject_id"] != topic["subject_id"]:
                raise ValueError(f"Topic '{topic['name']}' has an invalid parent topic.")
            visited = {topic["id"]}
            while parent is not None:
                if parent["id"] in visited:
                    raise ValueError(f"Topic '{topic['name']}' is part of a parent cycle.")
                visited.add(parent["id"])
                parent = topics_by_id.get(parent.get("parent_id"))


def load_data():
    if not DATA_FILE.exists():
        data = create_empty_data()
        save_data(data)
    else:
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"Cannot load invalid JSON from '{DATA_FILE}': {error}") from error

        validate_data(data, allow_missing_subject_ids=True)
        subjects_updated = False
        for subject in data["subjects"]:
            if not subject.get("id"):
                subject["id"] = str(uuid.uuid4())
                subjects_updated = True
        if subjects_updated:
            save_data(data)
    return data


def save_data(data):
    validate_data(data)
    temporary_path = DATA_FILE.with_name(f".{DATA_FILE.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
            file.flush()
            os.fsync(file.fileno())

        if DATA_FILE.exists():
            backup_path = DATA_FILE.with_suffix(DATA_FILE.suffix + ".bak")
            shutil.copy2(DATA_FILE, backup_path)

        os.replace(temporary_path, DATA_FILE)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def add_subject(data):
    subject_name = input("Enter the name of the new subject: ").strip()
    if not subject_name:
        print("Subject name cannot be empty.")
        return
    subject_name = subject_name.title()
    if any(subject["name"] == subject_name for subject in data["subjects"]):
        print(f"Subject '{subject_name}' already exists.")
        return  
    data["subjects"].append({"name": subject_name, "id": str(uuid.uuid4())})
    save_data(data)
    print(f"Subject '{subject_name}' added successfully.")


def view_subjects(data):
    subjects = [subject for subject in data["subjects"] if not subject.get("archived", False)]
    if not subjects:
        print("No active subjects found.")
        return
    print("Subjects:")
    for subject in subjects:
        print(f"- {subject['name']} (ID: {subject['id']})")


def edit_subject(data):
    subject_id = input("Enter the ID of the subject to rename: ").strip()
    subject = next((subject for subject in data["subjects"] if subject["id"] == subject_id), None)
    if subject is None:
        print("Subject not found.")
        return

    subject_name = input("Enter the new subject name: ").strip()
    if not subject_name:
        print("Subject name cannot be empty.")
        return
    subject_name = subject_name.title()
    if any(
        existing["id"] != subject_id and existing["name"] == subject_name
        for existing in data["subjects"]
    ):
        print(f"Subject '{subject_name}' already exists.")
        return

    subject["name"] = subject_name
    save_data(data)
    print(f"Subject renamed to '{subject_name}'.")


def archive_subject(data):
    subject_id = input("Enter the ID of the subject to archive: ").strip()
    subject = next((subject for subject in data["subjects"] if subject["id"] == subject_id), None)
    if subject is None:
        print("Subject not found.")
        return
    if subject.get("archived", False):
        print(f"Subject '{subject['name']}' is already archived.")
        return

    subject["archived"] = True
    save_data(data)
    print(f"Subject '{subject['name']}' archived. Its history has been kept.")


def delete_subject(data):
    subject_id = input("Enter the ID of the subject to permanently delete: ").strip()
    subject = next((subject for subject in data["subjects"] if subject["id"] == subject_id), None)
    if subject is None:
        print("Subject not found.")
        return

    print(
        f"WARNING: Permanently deleting '{subject['name']}' will also delete its related "
        "topics, sessions, revisions, exams, and goals. This cannot be undone."
    )
    confirmation = input("Type DELETE to confirm permanent deletion: ").strip()
    if confirmation != "DELETE":
        print("Permanent deletion cancelled.")
        return

    data["subjects"].remove(subject)
    for collection_name in ("topics", "sessions", "revisions", "exams", "goals"):
        data[collection_name] = [
            record
            for record in data[collection_name]
            if record.get("subject_id") != subject_id
        ]
    save_data(data)
    print(f"Subject '{subject['name']}' and its related records were permanently deleted.")


def _prompt_topic_choice(prompt, choices, current=None):
    choices_text = ", ".join(choices)
    if current is None:
        answer = input(f"{prompt} ({choices_text}): ").strip()
    else:
        answer = input(f"{prompt} ({choices_text}, Enter to keep {current}): ").strip()
        if not answer:
            return current

    selected = next((choice for choice in choices if choice.casefold() == answer.casefold()), None)
    if selected is None:
        print(f"Invalid choice. Choose one of: {choices_text}.")
    return selected


def add_topic(data):
    subject_id = input("Enter the ID of the subject for this topic: ").strip()
    subject = next(
        (
            subject
            for subject in data["subjects"]
            if subject["id"] == subject_id and not subject.get("archived", False)
        ),
        None,
    )
    if subject is None:
        print("Active subject not found.")
        return

    topic_name = input("Enter the topic name: ").strip()
    if not topic_name:
        print("Topic name cannot be empty.")
        return
    topic_name = topic_name.title()
    if any(
        topic["subject_id"] == subject_id
        and topic["name"].strip().casefold() == topic_name.casefold()
        for topic in data["topics"]
    ):
        print(f"Topic '{topic_name}' already exists in this subject.")
        return

    parent_id = input("Enter a parent topic ID for a subtopic, or leave blank: ").strip() or None
    if parent_id is not None and not any(
        topic["id"] == parent_id
        and topic["subject_id"] == subject_id
        and not topic.get("archived", False)
        for topic in data["topics"]
    ):
        print("Active parent topic not found in the selected subject.")
        return

    difficulty = _prompt_topic_choice("Difficulty", TOPIC_DIFFICULTIES)
    if difficulty is None:
        return
    priority = _prompt_topic_choice("Priority", TOPIC_PRIORITIES)
    if priority is None:
        return
    status = _prompt_topic_choice("Completion status", TOPIC_STATUSES)
    if status is None:
        return

    topic = {
        "id": str(uuid.uuid4()),
        "subject_id": subject_id,
        "name": topic_name,
        "parent_id": parent_id,
        "difficulty": difficulty,
        "priority": priority,
        "status": status,
    }
    data["topics"].append(topic)
    save_data(data)
    print(f"Topic '{topic_name}' added to '{subject['name']}'.")


def view_topics(data):
    subject_id = input("Enter the ID of the subject whose topics you want to view: ").strip()
    subject = next(
        (
            subject
            for subject in data["subjects"]
            if subject["id"] == subject_id and not subject.get("archived", False)
        ),
        None,
    )
    if subject is None:
        print("Active subject not found.")
        return

    topics = [
        topic
        for topic in data["topics"]
        if topic["subject_id"] == subject_id and not topic.get("archived", False)
    ]
    if not topics:
        print(f"No active topics found for '{subject['name']}'.")
        return

    topics_by_parent = {}
    for topic in topics:
        topics_by_parent.setdefault(topic.get("parent_id"), []).append(topic)

    print(f"Topics for '{subject['name']}':")

    def print_topic_tree(parent_id=None, depth=0):
        for topic in topics_by_parent.get(parent_id, []):
            indent = "  " * depth
            print(
                f"{indent}- {topic['name']} (ID: {topic['id']}; "
                f"Difficulty: {topic['difficulty']}; Priority: {topic['priority']}; "
                f"Status: {topic['status']})"
            )
            print_topic_tree(topic["id"], depth + 1)

    print_topic_tree()


def edit_topic(data):
    topic_id = input("Enter the ID of the topic to edit: ").strip()
    topic = next((topic for topic in data["topics"] if topic["id"] == topic_id), None)
    if topic is None or topic.get("archived", False):
        print("Active topic not found.")
        return

    topic_name = input(f"Enter the new topic name (Enter to keep {topic['name']}): ").strip()
    if topic_name:
        topic_name = topic_name.title()
        if any(
            other["id"] != topic_id
            and other["subject_id"] == topic["subject_id"]
            and other["name"].strip().casefold() == topic_name.casefold()
            for other in data["topics"]
        ):
            print(f"Topic '{topic_name}' already exists in this subject.")
            return
    else:
        topic_name = topic["name"]

    difficulty = _prompt_topic_choice(
        "Difficulty", TOPIC_DIFFICULTIES, current=topic["difficulty"]
    )
    if difficulty is None:
        return
    priority = _prompt_topic_choice("Priority", TOPIC_PRIORITIES, current=topic["priority"])
    if priority is None:
        return
    status = _prompt_topic_choice("Completion status", TOPIC_STATUSES, current=topic["status"])
    if status is None:
        return

    topic.update(
        {
            "name": topic_name,
            "difficulty": difficulty,
            "priority": priority,
            "status": status,
        }
    )
    save_data(data)
    print(f"Topic '{topic_name}' updated.")


def archive_topic(data):
    topic_id = input("Enter the ID of the topic to archive: ").strip()
    topic = next((topic for topic in data["topics"] if topic["id"] == topic_id), None)
    if topic is None:
        print("Topic not found.")
        return
    if topic.get("archived", False):
        print(f"Topic '{topic['name']}' is already archived.")
        return

    topic["archived"] = True
    save_data(data)
    print(f"Topic '{topic['name']}' archived.")


def main():
    data = load_data()
    
    print("Welcome to StudyFlow!")

    while True:
        print("\n1. View subjects")
        print("2. Add a subject")
        print("3. Edit a subject")
        print("4. Archive a subject")
        print("5. Permanently delete a subject")
        print("6. Exit")
        print("7. View topics for a subject")
        print("8. Add a topic or subtopic")
        print("9. Edit a topic")
        print("10. Archive a topic")

        choice = input("Enter your choice: ")

        if choice == "6":
            print("Goodbye! Keep learning with StudyFlow!")
            break
        elif choice == "1":
            view_subjects(data)

        elif choice == "2":
            add_subject(data)
        elif choice == "3":
            edit_subject(data)
        elif choice == "4":
            archive_subject(data)
        elif choice == "5":
            delete_subject(data)
        elif choice == "7":
            view_topics(data)
        elif choice == "8":
            add_topic(data)
        elif choice == "9":
            edit_topic(data)
        elif choice == "10":
            archive_topic(data)
        else:
            print("Invalid choice. Please enter a number from 1 to 10.")
        

if __name__ == "__main__":
    main()          
