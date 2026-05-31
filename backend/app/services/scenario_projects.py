from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.interview import InterviewSession, ProjectFile, Scenario, ScenarioProject, SessionFileSnapshot
from app.schemas.project import GeneratedScenarioProject


def upsert_scenario_project(
    db: Session,
    *,
    scenario: Scenario,
    project_payload: GeneratedScenarioProject | None,
) -> ScenarioProject | None:
    if project_payload is None:
        return scenario.project

    project = db.execute(
        select(ScenarioProject)
        .options(selectinload(ScenarioProject.files))
        .where(ScenarioProject.scenario_id == scenario.id)
    ).scalar_one_or_none()
    if project is None:
        project = ScenarioProject(scenario_id=scenario.id)
        db.add(project)

    project.stack = list(project_payload.stack)
    project.project_name = project_payload.project_name
    project.description = project_payload.description
    project.run_command = project_payload.run_command
    project.test_command = project_payload.test_command
    project.install_command = project_payload.install_command
    project.entrypoint = project_payload.entrypoint
    project.package_manager = project_payload.package_manager
    project.framework = project_payload.framework

    existing_files = {project_file.path: project_file for project_file in project.files}
    incoming_paths: set[str] = set()
    for file_payload in project_payload.files:
        incoming_paths.add(file_payload.path)
        project_file = existing_files.get(file_payload.path)
        if project_file is None:
            project_file = ProjectFile(project=project, path=file_payload.path)
            db.add(project_file)

        project_file.content = file_payload.content
        project_file.language = file_payload.language
        project_file.file_type = file_payload.file_type.value
        project_file.is_editable = file_payload.is_editable
        project_file.is_hidden = file_payload.is_hidden

    stale_files = [project_file for project_file in project.files if project_file.path not in incoming_paths]
    if stale_files:
        referenced_file_ids = set(
            db.execute(
                select(SessionFileSnapshot.project_file_id).where(
                    SessionFileSnapshot.project_file_id.in_([project_file.id for project_file in stale_files])
                )
            ).scalars()
        )
        for stale_file in stale_files:
            if stale_file.id in referenced_file_ids:
                stale_file.is_editable = False
                stale_file.is_hidden = True
                stale_file.file_type = "metadata"
            else:
                db.delete(stale_file)

    return project


def ensure_session_file_snapshots(db: Session, *, session: InterviewSession) -> list[SessionFileSnapshot]:
    scenario = session.interview.scenario
    if scenario is None:
        return []

    project = db.execute(
        select(ScenarioProject)
        .options(selectinload(ScenarioProject.files))
        .where(ScenarioProject.scenario_id == scenario.id)
    ).scalar_one_or_none()
    if project is None:
        return []

    existing_snapshots = {
        snapshot.project_file_id: snapshot
        for snapshot in db.execute(
            select(SessionFileSnapshot).where(SessionFileSnapshot.session_id == session.id)
        ).scalars()
    }
    existing_paths = {snapshot.path for snapshot in existing_snapshots.values()}
    snapshots = list(existing_snapshots.values())

    for project_file in project.files:
        if project_file.id in existing_snapshots or project_file.path in existing_paths:
            continue

        snapshot = SessionFileSnapshot(
            session_id=session.id,
            project_file_id=project_file.id,
            path=project_file.path,
            original_content=project_file.content,
            current_content=project_file.content,
            language=project_file.language,
        )
        db.add(snapshot)
        snapshots.append(snapshot)
        existing_paths.add(project_file.path)

    return sorted(snapshots, key=lambda snapshot: snapshot.path)
