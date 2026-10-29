import json
import os
import shutil
import uuid

import project


def data_with_subjects(subjects):
    data = project.create_empty_data()
    data["subjects"] = subjects
    return data


def topic_record(topic_id, subject_id, name, **updates):
    topic = {
        "id": topic_id,
        "subject_id": subject_id,
        "name": name,
        "parent_id": None,
        "difficulty": "Medium",
        "priority": "Medium",
        "status": "Not started",
    }
    topic.update(updates)
    return topic


def test_add_subject_saves_dictionary_with_unique_id(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([])
    monkeypatch.setattr("builtins.input", lambda _: "biology")

    project.add_subject(data)

    subject = data["subjects"][0]
    assert subject["name"] == "Biology"
    assert uuid.UUID(subject["id"])
    assert json.loads(data_file.read_text()) == data


def test_add_subject_rejects_duplicate_and_does_not_save(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects(
        [{"name": "Biology", "id": "subject-1", "archived": True}]
    )
    monkeypatch.setattr("builtins.input", lambda _: "biology")

    project.add_subject(data)

    assert len(data["subjects"]) == 1
    assert not data_file.exists()
    assert "already exists" in capsys.readouterr().out


def test_view_subjects_displays_names_and_ids(capsys):
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])

    project.view_subjects(data)

    assert "- Biology (ID: subject-1)" in capsys.readouterr().out


def test_edit_subject_renames_and_saves(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    answers = iter(["subject-1", "chemistry"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.edit_subject(data)

    assert data["subjects"][0] == {"name": "Chemistry", "id": "subject-1"}
    assert json.loads(data_file.read_text()) == data


def test_archive_subject_hides_it_and_preserves_history(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    subject = {"name": "Biology", "id": "subject-1"}
    data = data_with_subjects([subject])
    data["topics"] = [topic_record("topic-1", "subject-1", "Cells")]
    monkeypatch.setattr("builtins.input", lambda _: "subject-1")

    project.archive_subject(data)
    project.view_subjects(data)

    assert subject["archived"] is True
    assert data["topics"] == [topic_record("topic-1", "subject-1", "Cells")]
    assert "No active subjects found." in capsys.readouterr().out
    assert json.loads(data_file.read_text()) == data


def test_delete_subject_removes_related_records_after_confirmation(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects(
        [
            {"name": "Biology", "id": "subject-1"},
            {"name": "Chemistry", "id": "subject-2"},
        ]
    )
    data.update(
        {
            "topics": [
                topic_record("topic-1", "subject-1", "Cells"),
                topic_record("topic-2", "subject-2", "Atoms"),
            ],
            "sessions": [{"subject_id": "subject-1"}],
            "revisions": [{"subject_id": "subject-1"}],
            "exams": [{"subject_id": "subject-1"}],
            "goals": [{"subject_id": "subject-1"}],
        }
    )
    answers = iter(["subject-1", "DELETE"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.delete_subject(data)

    assert data["subjects"] == [{"name": "Chemistry", "id": "subject-2"}]
    assert data["topics"] == [topic_record("topic-2", "subject-2", "Atoms")]
    assert all(not data[key] for key in ("sessions", "revisions", "exams", "goals"))
    assert json.loads(data_file.read_text()) == data
    assert "WARNING" in capsys.readouterr().out


def test_delete_subject_cancellation_keeps_data_unchanged(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [topic_record("topic-1", "subject-1", "Cells")]
    original_data = json.loads(json.dumps(data))
    answers = iter(["subject-1", "no"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.delete_subject(data)

    assert data == original_data
    assert not data_file.exists()


def test_load_data_assigns_ids_to_legacy_subjects(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    data = data_with_subjects([{"name": "Biology"}, {"name": "Chemistry", "id": ""}])
    data_file.write_text(json.dumps(data))
    monkeypatch.setattr(project, "DATA_FILE", data_file)

    loaded_data = project.load_data()

    assert all(uuid.UUID(subject["id"]) for subject in loaded_data["subjects"])
    assert json.loads(data_file.read_text()) == loaded_data
    assert json.loads(data_file.with_suffix(".json.bak").read_text()) == data


def test_load_data_invalid_json_preserves_file(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    original_contents = '{"subjects": ['
    data_file.write_text(original_contents)
    monkeypatch.setattr(project, "DATA_FILE", data_file)

    try:
        project.load_data()
    except ValueError as error:
        assert "invalid JSON" in str(error)
    else:
        raise AssertionError("Invalid JSON should raise ValueError")

    assert data_file.read_text() == original_contents


def test_save_data_validates_before_writing(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    data_file.write_text('{"existing": true}')
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    invalid_data = data_with_subjects([{"name": "Biology", "id": ""}])

    try:
        project.save_data(invalid_data)
    except ValueError as error:
        assert "non-empty string ID" in str(error)
    else:
        raise AssertionError("Invalid data should raise ValueError")

    assert data_file.read_text() == '{"existing": true}'
    assert not data_file.with_suffix(".json.bak").exists()


def test_save_data_creates_backup_before_overwriting(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    original_contents = json.dumps(project.create_empty_data())
    data_file.write_text(original_contents)
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    updated_data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])

    project.save_data(updated_data)

    assert json.loads(data_file.read_text()) == updated_data
    assert data_file.with_suffix(".json.bak").read_text() == original_contents


def test_save_data_backup_error_preserves_original_file(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    original_contents = json.dumps(project.create_empty_data())
    data_file.write_text(original_contents)
    monkeypatch.setattr(project, "DATA_FILE", data_file)

    def fail_copy(*args, **kwargs):
        raise OSError("backup failed")

    monkeypatch.setattr(shutil, "copy2", fail_copy)
    try:
        project.save_data(data_with_subjects([{"name": "Biology", "id": "subject-1"}]))
    except OSError as error:
        assert str(error) == "backup failed"
    else:
        raise AssertionError("Backup error should be raised")

    assert data_file.read_text() == original_contents
    assert not list(tmp_path.glob("*.tmp"))


def test_save_data_replace_error_preserves_original_and_backup(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    original_contents = json.dumps(project.create_empty_data())
    data_file.write_text(original_contents)
    monkeypatch.setattr(project, "DATA_FILE", data_file)

    def fail_replace(*args, **kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    try:
        project.save_data(data_with_subjects([{"name": "Biology", "id": "subject-1"}]))
    except OSError as error:
        assert str(error) == "replace failed"
    else:
        raise AssertionError("Replace error should be raised")

    assert data_file.read_text() == original_contents
    assert data_file.with_suffix(".json.bak").read_text() == original_contents
    assert not list(tmp_path.glob("*.tmp"))


def test_add_subject_rejects_empty_name_without_saving(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([])
    monkeypatch.setattr("builtins.input", lambda _: "  ")

    project.add_subject(data)

    assert data["subjects"] == []
    assert not data_file.exists()
    assert "cannot be empty" in capsys.readouterr().out


def test_load_data_file_error_is_not_suppressed(tmp_path, monkeypatch):
    data_file = tmp_path / "missing" / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)

    try:
        project.load_data()
    except OSError:
        pass
    else:
        raise AssertionError("File creation error should be raised")


def test_add_topic_links_subject_and_parent_with_metadata(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [topic_record("parent-id", "subject-1", "Cells")]
    answers = iter(
        ["subject-1", "mitosis", "parent-id", "hard", "high", "in progress"]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.add_topic(data)

    subtopic = data["topics"][1]
    assert subtopic["name"] == "Mitosis"
    assert subtopic["subject_id"] == "subject-1"
    assert subtopic["parent_id"] == "parent-id"
    assert subtopic["difficulty"] == "Hard"
    assert subtopic["priority"] == "High"
    assert subtopic["status"] == "In progress"
    assert uuid.UUID(subtopic["id"])
    assert json.loads(data_file.read_text()) == data


def test_add_topic_rejects_duplicate_name_case_insensitively(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects(
        [
            {"name": "Biology", "id": "subject-1"},
            {"name": "Chemistry", "id": "subject-2"},
        ]
    )
    data["topics"] = [topic_record("topic-1", "subject-1", "Cell Biology")]
    answers = iter(["subject-1", " cell biology "])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.add_topic(data)

    assert len(data["topics"]) == 1
    assert not data_file.exists()
    assert "already exists" in capsys.readouterr().out


def test_add_topic_rejects_empty_name(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    answers = iter(["subject-1", "   "])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.add_topic(data)

    assert data["topics"] == []
    assert not data_file.exists()
    assert "cannot be empty" in capsys.readouterr().out


def test_topic_names_can_repeat_in_different_subjects():
    data = data_with_subjects(
        [
            {"name": "Biology", "id": "subject-1"},
            {"name": "Chemistry", "id": "subject-2"},
        ]
    )
    data["topics"] = [
        topic_record("topic-1", "subject-1", "Atoms"),
        topic_record("topic-2", "subject-2", "Atoms"),
    ]

    project.validate_data(data)


def test_add_topic_rejects_invalid_name_parent_and_metadata(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    answers = iter(
        ["subject-1", "Cells", "missing-parent", "subject-1", "Cells", "", "impossible"]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.add_topic(data)
    project.add_topic(data)

    assert data["topics"] == []
    assert not data_file.exists()
    output = capsys.readouterr().out
    assert "parent topic not found" in output
    assert "Invalid choice" in output


def test_view_topics_displays_subject_topics_and_subtopics(capsys, monkeypatch):
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [
        topic_record("topic-1", "subject-1", "Cells"),
        topic_record(
            "topic-2", "subject-1", "Mitosis", parent_id="topic-1",
            difficulty="Hard", priority="High", status="In progress"
        ),
        topic_record("topic-3", "subject-1", "Hidden", archived=True),
        topic_record("topic-4", "other-subject", "Other"),
    ]
    monkeypatch.setattr("builtins.input", lambda _: "subject-1")

    project.view_topics(data)

    output = capsys.readouterr().out
    assert "Cells" in output
    assert "Mitosis" in output
    assert "Difficulty: Hard" in output
    assert "Priority: High" in output
    assert "Status: In progress" in output
    assert "Hidden" not in output
    assert "Other" not in output


def test_edit_topic_updates_name_and_metadata(tmp_path, monkeypatch):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    original = topic_record("topic-1", "subject-1", "Cells")
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [original]
    answers = iter(["topic-1", "genetics", "hard", "high", "completed"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.edit_topic(data)

    assert original["name"] == "Genetics"
    assert original["difficulty"] == "Hard"
    assert original["priority"] == "High"
    assert original["status"] == "Completed"
    assert json.loads(data_file.read_text()) == data


def test_edit_topic_rejects_duplicate_and_invalid_values(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [
        topic_record("topic-1", "subject-1", "Cells"),
        topic_record("topic-2", "subject-1", "Genetics"),
    ]
    answers = iter(["topic-2", "cells", "topic-2", "Genetics", "invalid"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    project.edit_topic(data)
    project.edit_topic(data)

    assert data["topics"][1]["name"] == "Genetics"
    assert not data_file.exists()
    output = capsys.readouterr().out
    assert "already exists" in output
    assert "Invalid choice" in output


def test_archive_topic_hides_topic_but_preserves_subtopic(tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "studyflow_data.json"
    monkeypatch.setattr(project, "DATA_FILE", data_file)
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [
        topic_record("topic-1", "subject-1", "Cells"),
        topic_record("topic-2", "subject-1", "Mitosis", parent_id="topic-1"),
    ]
    monkeypatch.setattr("builtins.input", lambda _: "topic-1")

    project.archive_topic(data)
    answers = iter(["subject-1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    project.view_topics(data)

    assert data["topics"][0]["archived"] is True
    assert data["topics"][1].get("archived", False) is False
    assert "Mitosis" not in capsys.readouterr().out
    assert json.loads(data_file.read_text()) == data


def test_validate_data_rejects_invalid_topic_links_and_fields():
    data = data_with_subjects([{"name": "Biology", "id": "subject-1"}])
    data["topics"] = [
        topic_record("topic-1", "missing-subject", "Cells")
    ]

    try:
        project.validate_data(data)
    except ValueError as error:
        assert "unknown subject ID" in str(error)
    else:
        raise AssertionError("Invalid topic subject ID should be rejected")
