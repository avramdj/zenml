import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)

PRIORITIES = {"LOWEST": 5, "LOW": 4, "MEDIUM": 3, "HIGH": 2, "HIGHEST": 1}

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"]
JIRA_USERNAME = os.environ["JIRA_USERNAME"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]

JIRA_BOARD_ID = os.environ["JIRA_BOARD_ID"]
JIRA_ISSUE_TYPE_ID = os.environ["JIRA_ISSUE_TYPE_ID"]
JIRA_DONE_STATUS_CATEGORY_ID = int(os.environ["JIRA_DONE_STATUS_CATEGORY_ID"])
JIRA_ISSUE_LABEL = os.environ["JIRA_ISSUE_LABEL"]


class Todo:
    """Represents a TODO comment in code."""

    def __init__(
        self,
        filepath: str,
        description: str,
        priority: Optional[str] = None,
        issue_key: Optional[str] = None,
    ):
        self.filepath = filepath
        self.description = description
        self.priority = priority
        self.issue_key = issue_key


class JiraIssue:
    """Represents an issue from a JIRA board."""

    def __init__(self, key: str, done: bool):
        self.key = key
        self.done = done


def issue_payload_for_todo(todo: Todo) -> Dict[str, Any]:
    """Returns the http request data required to create a JIRA issue for the
    given Todo object."""
    title = f"Autogenerated issue from TODO comment in file {todo.filepath}."
    return {
        "fields": {
            "summary": title,
            "issuetype": {"id": f"{JIRA_ISSUE_TYPE_ID}"},
            "project": {"id": f"{JIRA_BOARD_ID}"},
            "priority": {"id": f"{PRIORITIES[todo.priority]}"},
            "labels": [JIRA_ISSUE_LABEL],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"text": todo.description, "type": "text"}],
                    }
                ],
            },
        },
    }


def create_jira_issues(session: requests.Session, todos: List[Todo]) -> None:
    """Creates JIRA issues for the given Todos and updates their issue keys."""
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/bulk"

    data = json.dumps(
        {"issueUpdates": [issue_payload_for_todo(todo) for todo in todos]}
    )

    try:
        response = session.post(url, data=data)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error("Failed to create JIRA issues: %s", e)
        sys.exit()

    issues = json.loads(response.text)["issues"]
    for todo, issue in zip(todos, issues):
        todo.issue_key = issue["key"]


def get_all_jira_todo_issues(session: requests.Session) -> List[JiraIssue]:
    """Returns a list of all JIRA issues in the board specified by
    `JIRA_BOARD_ID` and the label specified in `JIRA_ISSUE_LABEL`."""
    url = f"{JIRA_BASE_URL}/rest/api/3/search"

    parameters = {
        "jql": f'project = "{JIRA_BOARD_ID}" AND labels = "{JIRA_ISSUE_LABEL}"',
        "fields": "status",
        "maxResults": 500,
    }

    try:
        response = session.get(url, params=parameters)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error("Failed to retrieve JIRA todo issues: %s", e)
        sys.exit()

    issues = []
    for issue_dict in response.json()["issues"]:
        status_category = issue_dict["fields"]["status"]["statusCategory"]["id"]
        is_done = status_category == JIRA_DONE_STATUS_CATEGORY_ID
        issues.append(JiraIssue(key=issue_dict["key"], done=is_done))

    return issues


def remove_todos_for_closed_issues(
    file: Path, todos: List[Todo], issues: List[JiraIssue]
) -> None:
    """Removes Todos if their referenced issue was closed.

    Args:
        file: The file for which to remove the todos.
        todos: All todos with existing JIRA issues found in this file.
        issues: All jira issues referring to code todos.
    """
    open_issue_keys = {issue.key for issue in issues if not issue.done}
    todos_to_delete = [
        todo.issue_key
        for todo in todos
        if todo.issue_key not in open_issue_keys
    ]

    if todos_to_delete:
        file_content = file.read_text()

        regex = re.compile(
            r"(^[ \t]*#) TODO ?\[("
            + "|".join(todos_to_delete)
            + r")\] ?:(.*$\n(\1 {2}.*$\n)*)",
            flags=re.MULTILINE,
        )
        new_file_content = re.sub(
            regex,
            "",
            file_content,
        )

        file.write_text(new_file_content)
        logging.info(
            "Deleted %d todos in file '%s'.", len(todos_to_delete), file
        )


def find_todos(file: Path) -> Tuple[List[Todo], List[Todo]]:
    """Finds Todo comments in a file.

    Args:
        file: The file to search.

    Returns: A tuple (todos_without_issue, todos_with_issue) for todos
        without/with a corresponding JIRA issue.
    """
    file_content = file.read_text()

    matches = re.findall(
        r"(^[ \t]*#) TODO ?\[(LOWEST|LOW|MEDIUM|HIGH|HIGHEST|[A-Z]*?-[0-9]*?)\]"
        r" ?:(.*$\n(\1 {2}.*$\n)*)",
        file_content,
        flags=re.MULTILINE,
    )

    todos_without_issue = []
    todos_with_issue = []

    for _, priority_or_key, description, _ in matches:
        # remove whitespace and leading '#' from description
        lines = description.strip().split("\n")
        lines = [line.strip().lstrip("#").strip() for line in lines]
        description = " ".join(lines)

        todo = Todo(filepath=str(file), description=description)
        if priority_or_key in PRIORITIES:
            todo.priority = priority_or_key
            todos_without_issue.append(todo)
        else:
            todo.issue_key = priority_or_key
            todos_with_issue.append(todo)

    logging.info(
        "Found %d todos without a corresponding JIRA issue and %d todos "
        "with a JIRA issue in file '%s'.",
        len(todos_without_issue),
        len(todos_with_issue),
        file,
    )

    return todos_without_issue, todos_with_issue


def update_file_with_issue_keys(file: Path, todos: List[Todo]) -> None:
    """Replaces TODO priorities by the issue key that the TODO is referencing.

    Args:
        file: The file in which the todos will be replaced.
        todos: The todos to replace.
    """
    file_content = file.read_text()
    todo_iterator = iter(todos)

    def _replace(match):
        todo = next(todo_iterator)
        result = match.group(1) + f"{todo.issue_key}" + match.group(4)
        return result

    new_file_content = re.sub(
        r"((^[ \t]*#) TODO ?\[)(LOWEST|LOW|MEDIUM|HIGH|HIGHEST)(\] ?:"
        r".*$\n(\2 {2}.*$\n)*)",
        _replace,
        file_content,
        flags=re.MULTILINE,
    )

    file.write_text(new_file_content)
    logging.info(
        "Added JIRA issue keys for %d todos in file '%s'.", len(todos), file
    )


def update_todos(python_files: List[Path]) -> None:
    """Updates TODO comments.

    This method
    - creates JIRA issues for all TODO comments that don't have a
        corresponding JIRA issue yet
    - removes TODO comments which reference a JIRA issue that was closed

    Args:
        python_files: Python files to search for todos
    """
    session = _setup_session()
    jira_issues = get_all_jira_todo_issues(session)

    for file in python_files:
        todos_without_issue, todos_with_issue = find_todos(file)

        if todos_with_issue:
            remove_todos_for_closed_issues(file, todos_with_issue, jira_issues)

        if todos_without_issue:
            create_jira_issues(session, todos_without_issue)
            update_file_with_issue_keys(file, todos_without_issue)


def _setup_session() -> requests.Session:
    """Creates a requests session that handles authentication and retrying."""
    session = requests.session()

    retries = Retry(
        total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount(JIRA_BASE_URL, adapter)
    session.auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)
    session.headers.update(
        {"Accept": "application/json", "Content-Type": "application/json"}
    )

    return session


def _parse_args() -> argparse.Namespace:
    """Parses the root directory from command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update Todos for python files in a directory."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="The directory to search for python files.",
    )

    return parser.parse_args()


def main():
    """Updates todos for all python files in the directory specified as
    command line argument."""
    root_directory = _parse_args().directory
    python_files = root_directory.rglob("*.py")
    update_todos(python_files)


if __name__ == "__main__":
    main()
