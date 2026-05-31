from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
import re
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from app.core.config import Settings, settings


class UnsafeRepositoryFileError(ValueError):
    pass


class GitHubSubmissionPushError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubSubmissionFile:
    path: str
    content: str


@dataclass(frozen=True)
class GitHubSubmissionPushResult:
    status: str
    branch_name: str | None = None
    base_branch_name: str | None = None
    commit_sha: str | None = None
    repository_url: str | None = None
    pull_request_url: str | None = None
    error: str | None = None


_UNSAFE_PATH_PARTS = {".env"}
_UNSAFE_PATH_PREFIXES = (".env.",)
_PRIVATE_KEY_PATH_MARKERS = (
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "private_key",
    "private-key",
)
_PRIVATE_KEY_SUFFIXES = (".pem", ".key", ".p8")
_SECRET_CONTENT_MARKERS = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
)
_SECRET_ASSIGNMENT_MARKERS = (
    "GITHUB_TOKEN=",
    "OPENAI_API_KEY=",
    "JWT_SECRET=",
)
_BRANCH_SLUG_RE = re.compile(r"[^a-z0-9]+")


def validate_repository_file(path: str, content: str) -> str:
    cleaned = path.strip().replace("\\", "/")
    pure_path = PurePosixPath(cleaned)
    parts = tuple(part.lower() for part in pure_path.parts)
    filename = parts[-1] if parts else ""

    if not cleaned or cleaned.startswith("/") or pure_path.is_absolute() or ".." in pure_path.parts:
        raise UnsafeRepositoryFileError("Submitted file paths must be relative and cannot contain parent traversal.")
    if pure_path.parts and ":" in pure_path.parts[0]:
        raise UnsafeRepositoryFileError("Submitted file paths cannot contain drive letters.")
    if any(part in _UNSAFE_PATH_PARTS or part.startswith(_UNSAFE_PATH_PREFIXES) for part in parts):
        raise UnsafeRepositoryFileError("Submitted files cannot include environment files.")
    if any(marker in cleaned.lower() for marker in _PRIVATE_KEY_PATH_MARKERS) or filename.endswith(_PRIVATE_KEY_SUFFIXES):
        raise UnsafeRepositoryFileError("Submitted files cannot include private key material.")
    if any(marker in content for marker in _SECRET_CONTENT_MARKERS):
        raise UnsafeRepositoryFileError("Submitted files cannot include private key material.")
    if any(marker in content.upper() for marker in _SECRET_ASSIGNMENT_MARKERS):
        raise UnsafeRepositoryFileError("Submitted files cannot include secret environment values.")
    return cleaned


def _timestamp_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


def _branch_slug(value: str, *, fallback: str, max_length: int = 48) -> str:
    slug = _BRANCH_SLUG_RE.sub("-", value.strip().lower()).strip("-")
    if not slug:
        slug = fallback
    return slug[:max_length].strip("-") or fallback


def build_scenario_branch_name(*, interview_id: UUID, scenario_id: UUID, generated_at: datetime) -> str:
    timestamp = _timestamp_utc(generated_at)
    return f"scenario-interview-{str(interview_id)[:8]}-{str(scenario_id)[:8]}-{timestamp}"


def build_submission_branch_name(
    *,
    interview_id: UUID,
    session_id: UUID,
    candidate_email: str,
    submitted_at: datetime,
) -> str:
    timestamp = _timestamp_utc(submitted_at)
    candidate_slug = _branch_slug(candidate_email, fallback="candidate")
    return f"candidate-{candidate_slug}-interview-{str(interview_id)[:8]}-session-{str(session_id)[:8]}-{timestamp}"


class GitHubSubmissionPublisher:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    @property
    def repository_url(self) -> str | None:
        owner = self.settings.github_owner.strip()
        repo = self.settings.github_repo.strip()
        if not owner or not repo:
            return None
        return f"https://github.com/{owner}/{repo}"

    @property
    def is_configured(self) -> bool:
        return all(
            [
                self.settings.github_token.strip(),
                self.settings.github_owner.strip(),
                self.settings.github_repo.strip(),
            ]
        )

    def publish_submission(
        self,
        *,
        interview_id: UUID,
        session_id: UUID,
        candidate_email: str,
        submitted_at: datetime,
        files: list[GitHubSubmissionFile],
        candidate_notes: str,
        base_branch_name: str | None = None,
    ) -> GitHubSubmissionPushResult:
        safe_files = [
            GitHubSubmissionFile(path=validate_repository_file(file.path, file.content), content=file.content)
            for file in files
        ]
        repository_url = self.repository_url
        if not self.is_configured:
            return GitHubSubmissionPushResult(
                status="not_configured",
                base_branch_name=base_branch_name,
                repository_url=repository_url,
            )
        if not safe_files:
            return GitHubSubmissionPushResult(
                status="no_changes",
                base_branch_name=base_branch_name,
                repository_url=repository_url,
            )

        branch_name = build_submission_branch_name(
            interview_id=interview_id,
            session_id=session_id,
            candidate_email=candidate_email,
            submitted_at=submitted_at,
        )
        try:
            should_create_pr = bool(base_branch_name) or self.settings.github_create_pr
            return self._publish_to_github(
                branch_name=branch_name,
                base_branch_name=base_branch_name,
                files=safe_files,
                commit_message=f"Submit Nexterview solution for {candidate_email}",
                pull_request_title=f"Nexterview submission: {candidate_email}",
                pull_request_body=(
                    "Candidate submission created by Nexterview.\n\n"
                    f"Candidate: `{candidate_email}`\n"
                    f"Session branch: `{branch_name}`\n"
                    f"Base branch: `{base_branch_name or self.settings.github_default_branch.strip() or 'main'}`\n"
                    f"Changed files: {len(safe_files)}\n\n"
                    f"Candidate notes:\n{candidate_notes or 'No notes provided.'}"
                ),
                create_pull_request=should_create_pr,
            )
        except GitHubSubmissionPushError as exc:
            return GitHubSubmissionPushResult(
                status="failed",
                branch_name=branch_name,
                base_branch_name=base_branch_name,
                repository_url=repository_url,
                error=str(exc)[:1000],
            )
        except httpx.HTTPError:
            return GitHubSubmissionPushResult(
                status="failed",
                branch_name=branch_name,
                base_branch_name=base_branch_name,
                repository_url=repository_url,
                error="GitHub request failed.",
            )

    def publish_scenario_project(
        self,
        *,
        interview_id: UUID,
        scenario_id: UUID,
        generated_at: datetime,
        files: list[GitHubSubmissionFile],
    ) -> GitHubSubmissionPushResult:
        repository_url = self.repository_url
        try:
            safe_files = [
                GitHubSubmissionFile(path=validate_repository_file(file.path, file.content), content=file.content)
                for file in files
            ]
        except UnsafeRepositoryFileError as exc:
            return GitHubSubmissionPushResult(status="failed", repository_url=repository_url, error=str(exc)[:1000])
        if not self.is_configured:
            return GitHubSubmissionPushResult(status="not_configured", repository_url=repository_url)
        if not safe_files:
            return GitHubSubmissionPushResult(status="no_changes", repository_url=repository_url)

        branch_name = build_scenario_branch_name(
            interview_id=interview_id,
            scenario_id=scenario_id,
            generated_at=generated_at,
        )
        try:
            return self._publish_to_github(
                branch_name=branch_name,
                base_branch_name=None,
                files=safe_files,
                commit_message=f"Create Nexterview starter project for interview {interview_id}",
                pull_request_title=None,
                pull_request_body=None,
                create_pull_request=False,
            )
        except GitHubSubmissionPushError as exc:
            return GitHubSubmissionPushResult(
                status="failed",
                branch_name=branch_name,
                repository_url=repository_url,
                error=str(exc)[:1000],
            )
        except httpx.HTTPError:
            return GitHubSubmissionPushResult(
                status="failed",
                branch_name=branch_name,
                repository_url=repository_url,
                error="GitHub request failed.",
            )

    def _publish_to_github(
        self,
        *,
        branch_name: str,
        base_branch_name: str | None,
        files: list[GitHubSubmissionFile],
        commit_message: str,
        pull_request_title: str | None,
        pull_request_body: str | None,
        create_pull_request: bool,
    ) -> GitHubSubmissionPushResult:
        owner = self.settings.github_owner.strip()
        repo = self.settings.github_repo.strip()
        base_branch = base_branch_name or self.settings.github_default_branch.strip() or "main"
        repository_url = f"https://github.com/{owner}/{repo}"
        headers = {
            "Authorization": f"Bearer {self.settings.github_token.strip()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=20.0) as client:
            encoded_base_branch = quote(base_branch, safe="")
            default_ref = self._request(client, "GET", f"/repos/{owner}/{repo}/git/ref/heads/{encoded_base_branch}")
            base_sha = str(default_ref["object"]["sha"])
            base_commit = self._request(client, "GET", f"/repos/{owner}/{repo}/git/commits/{base_sha}")
            base_tree_sha = str(base_commit["tree"]["sha"])

            self._request(
                client,
                "POST",
                f"/repos/{owner}/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
            )

            tree_entries = []
            for file in files:
                blob = self._request(
                    client,
                    "POST",
                    f"/repos/{owner}/{repo}/git/blobs",
                    json={"content": file.content, "encoding": "utf-8"},
                )
                tree_entries.append({"path": file.path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

            tree = self._request(
                client,
                "POST",
                f"/repos/{owner}/{repo}/git/trees",
                json={"base_tree": base_tree_sha, "tree": tree_entries},
            )
            commit = self._request(
                client,
                "POST",
                f"/repos/{owner}/{repo}/git/commits",
                json={
                    "message": commit_message,
                    "tree": tree["sha"],
                    "parents": [base_sha],
                },
            )
            commit_sha = str(commit["sha"])
            self._request(
                client,
                "PATCH",
                f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
                json={"sha": commit_sha, "force": False},
            )

            pull_request_url = None
            if create_pull_request:
                pull_request = self._request(
                    client,
                    "POST",
                    f"/repos/{owner}/{repo}/pulls",
                    json={
                        "title": pull_request_title or f"Nexterview changes: {branch_name}",
                        "head": branch_name,
                        "base": base_branch,
                        "body": pull_request_body or "",
                    },
                )
                pull_request_url = str(pull_request.get("html_url") or "")

        return GitHubSubmissionPushResult(
            status="pushed",
            branch_name=branch_name,
            base_branch_name=base_branch_name,
            commit_sha=commit_sha,
            repository_url=repository_url,
            pull_request_url=pull_request_url or None,
        )

    def _request(
        self,
        client: httpx.Client,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = client.request(method, path, json=json)
        if response.status_code >= 400:
            raise GitHubSubmissionPushError(_safe_github_error(response))
        payload = response.json()
        if not isinstance(payload, dict):
            raise GitHubSubmissionPushError("GitHub returned an unexpected response.")
        return payload


def _safe_github_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"GitHub returned HTTP {response.status_code}."
    message = payload.get("message") if isinstance(payload, dict) else None
    if isinstance(message, str) and message:
        return f"GitHub returned HTTP {response.status_code}: {message[:300]}"
    return f"GitHub returned HTTP {response.status_code}."
