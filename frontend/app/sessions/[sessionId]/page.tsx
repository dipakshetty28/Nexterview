"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";

import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  askCandidateCopilot,
  getCandidateSession,
  getCandidateWorkspace,
  runSessionTests,
  saveSessionEvent,
  submitSessionSolution,
  updateWorkspaceFile,
} from "@/lib/api";
import type {
  AIMessage,
  CandidateSession,
  CandidateWorkspace,
  Submission,
  TestRunResult,
  WorkspaceFile,
} from "@/lib/types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-96 items-center justify-center bg-slate-950 text-sm text-slate-400">
      Loading editor...
    </div>
  ),
});

type TreeNode = {
  name: string;
  path: string;
  children: TreeNode[];
  file?: WorkspaceFile;
};

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
    .toString()
    .padStart(2, "0");
  const minutes = Math.floor((totalSeconds % 3600) / 60)
    .toString()
    .padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function formatSavedAt(value: string | null): string {
  if (!value) {
    return "Not saved yet";
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function languageForStack(stack: string[]): string {
  const joinedStack = stack.join(" ").toLowerCase();
  if (joinedStack.includes("python") || joinedStack.includes("fastapi")) {
    return "python";
  }
  if (joinedStack.includes("java") || joinedStack.includes("spring")) {
    return "java";
  }
  if (joinedStack.includes("c#") || joinedStack.includes(".net")) {
    return "csharp";
  }
  if (joinedStack.includes("go")) {
    return "go";
  }
  if (joinedStack.includes("react") || joinedStack.includes("next") || joinedStack.includes("node")) {
    return "typescript";
  }
  return "javascript";
}

function monacoLanguage(language: string): string {
  const normalized = language.toLowerCase();
  if (normalized === "md" || normalized === "markdown") {
    return "markdown";
  }
  if (normalized === "py") {
    return "python";
  }
  if (normalized === "tsx" || normalized === "jsx") {
    return "typescript";
  }
  if (normalized === "yml") {
    return "yaml";
  }
  if (normalized === "sh" || normalized === "bash") {
    return "shell";
  }
  return normalized;
}

function buildFileTree(files: WorkspaceFile[]): TreeNode[] {
  const root: TreeNode = { name: "", path: "", children: [] };

  for (const file of files) {
    const parts = file.path.split("/");
    let current = root;
    parts.forEach((part, index) => {
      const nodePath = parts.slice(0, index + 1).join("/");
      let child = current.children.find((item) => item.name === part);
      if (!child) {
        child = { name: part, path: nodePath, children: [] };
        current.children.push(child);
      }
      if (index === parts.length - 1) {
        child.file = file;
      }
      current = child;
    });
  }

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((left, right) => {
      if (left.file && !right.file) {
        return 1;
      }
      if (!left.file && right.file) {
        return -1;
      }
      return left.name.localeCompare(right.name);
    });
    nodes.forEach((node) => sortNodes(node.children));
  };
  sortNodes(root.children);
  return root.children;
}

function FileTreeItem({
  node,
  selectedFileId,
  dirtyFileIds,
  savingFileIds,
  onSelect,
  depth = 0,
}: {
  node: TreeNode;
  selectedFileId: string | null;
  dirtyFileIds: Set<string>;
  savingFileIds: Set<string>;
  onSelect: (file: WorkspaceFile) => void;
  depth?: number;
}) {
  if (node.file) {
    const isSelected = selectedFileId === node.file.id;
    const isDirty = dirtyFileIds.has(node.file.id);
    const isSaving = savingFileIds.has(node.file.id);
    return (
      <button
        className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-xs ${
          isSelected ? "bg-cyan-950/70 text-cyan-100" : "text-slate-300 hover:bg-slate-900"
        }`}
        onClick={() => onSelect(node.file as WorkspaceFile)}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        type="button"
      >
        <span className="min-w-0 truncate">{node.name}</span>
        <span className="shrink-0 text-[10px] text-slate-500">
          {isSaving ? "saving" : isDirty ? "*" : node.file.is_editable ? "" : "lock"}
        </span>
      </button>
    );
  }

  return (
    <details open>
      <summary
        className="cursor-pointer rounded-md px-2 py-1.5 text-xs font-semibold text-slate-400 hover:bg-slate-900"
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        {node.name}
      </summary>
      <div className="grid gap-0.5">
        {node.children.map((child) => (
          <FileTreeItem
            dirtyFileIds={dirtyFileIds}
            key={child.path}
            node={child}
            onSelect={onSelect}
            savingFileIds={savingFileIds}
            selectedFileId={selectedFileId}
            depth={depth + 1}
          />
        ))}
      </div>
    </details>
  );
}

function FileTree({
  files,
  selectedFileId,
  dirtyFileIds,
  savingFileIds,
  onSelect,
}: {
  files: WorkspaceFile[];
  selectedFileId: string | null;
  dirtyFileIds: Set<string>;
  savingFileIds: Set<string>;
  onSelect: (file: WorkspaceFile) => void;
}) {
  const tree = useMemo(() => buildFileTree(files), [files]);

  return (
    <div className="grid gap-1">
      {tree.map((node) => (
        <FileTreeItem
          dirtyFileIds={dirtyFileIds}
          key={node.path}
          node={node}
          onSelect={onSelect}
          savingFileIds={savingFileIds}
          selectedFileId={selectedFileId}
        />
      ))}
    </div>
  );
}

const markdownComponents: Components = {
  code({ className, children, node: _node, ...props }) {
    const match = /language-(\w+)/.exec(className ?? "");
    const codeText = String(children ?? "").replace(/\n$/, "");
    if (!match) {
      return (
        <code className="rounded bg-slate-800 px-1 py-0.5 text-cyan-200" {...props}>
          {children}
        </code>
      );
    }

    return <CopyableCodeBlock code={codeText} language={match[1]} />;
  },
  p({ children }) {
    return <p className="leading-6">{children}</p>;
  },
  ul({ children }) {
    return <ul className="ml-4 list-disc space-y-1">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="ml-4 list-decimal space-y-1">{children}</ol>;
  },
};

function CopyableCodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="my-3 overflow-hidden rounded-md border border-slate-800 bg-slate-950">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2 text-xs text-slate-400">
        <span>{language}</span>
        <button className="text-cyan-300 hover:text-cyan-200" onClick={() => void handleCopy()} type="button">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-auto p-3 text-xs leading-5 text-slate-200">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function CopilotMessage({ message }: { message: AIMessage }) {
  const isAssistant = message.role === "assistant";
  return (
    <div
      className={
        isAssistant
          ? "rounded-md border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200"
          : "rounded-md border border-cyan-950/70 bg-cyan-950/30 p-3 text-sm text-cyan-50"
      }
    >
      <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">{isAssistant ? "Copilot" : "You"}</p>
      {isAssistant ? (
        <div className="grid gap-2">
          <ReactMarkdown components={markdownComponents}>{message.content}</ReactMarkdown>
        </div>
      ) : (
        <p className="whitespace-pre-wrap leading-6">{message.content}</p>
      )}
    </div>
  );
}

function CandidateSessionContent() {
  const params = useParams<{ sessionId: string }>();
  const { token, user } = useAuth();
  const [session, setSession] = useState<CandidateSession | null>(null);
  const [workspace, setWorkspace] = useState<CandidateWorkspace | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [fileContents, setFileContents] = useState<Record<string, string>>({});
  const [dirtyFileIds, setDirtyFileIds] = useState<Set<string>>(new Set());
  const [savingFileIds, setSavingFileIds] = useState<Set<string>>(new Set());
  const [legacyCode, setLegacyCode] = useState("");
  const [notes, setNotes] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingCode, setIsSavingCode] = useState(false);
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [testRun, setTestRun] = useState<TestRunResult | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [copilotMessages, setCopilotMessages] = useState<AIMessage[]>([]);
  const [copilotQuestion, setCopilotQuestion] = useState("");
  const [isAskingCopilot, setIsAskingCopilot] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const legacyCodeSaveTimer = useRef<number | null>(null);
  const noteSaveTimer = useRef<number | null>(null);
  const fileSaveTimers = useRef<Record<string, number>>({});
  const latestFileContents = useRef<Record<string, string>>({});
  const openedFileIds = useRef<Set<string>>(new Set());
  const sessionStartedSent = useRef(false);

  const workspaceFiles = workspace?.files ?? [];
  const hasWorkspace = workspaceFiles.length > 0;
  const selectedFile = workspaceFiles.find((file) => file.id === selectedFileId) ?? null;
  const selectedEditorValue = selectedFile
    ? fileContents[selectedFile.id] ?? selectedFile.current_content
    : legacyCode;
  const isSubmitted = session?.status === "submitted" || session?.status === "reviewed";

  useEffect(() => {
    if (!token || !params.sessionId) {
      return;
    }

    setIsLoading(true);
    setError(null);
    Promise.all([getCandidateSession(token, params.sessionId), getCandidateWorkspace(token, params.sessionId)])
      .then(([loadedSession, loadedWorkspace]) => {
        const nextContents = Object.fromEntries(
          loadedWorkspace.files.map((file) => [file.id, file.current_content]),
        );
        const entrypointFile = loadedWorkspace.files.find((file) => file.path === loadedWorkspace.project?.entrypoint);
        const firstEditableSource =
          loadedWorkspace.files.find((file) => file.is_editable && file.file_type === "source") ??
          loadedWorkspace.files.find((file) => file.is_editable) ??
          loadedWorkspace.files[0] ??
          null;

        latestFileContents.current = nextContents;
        setSession(loadedSession);
        setWorkspace(loadedWorkspace);
        setSelectedFileId((entrypointFile ?? firstEditableSource)?.id ?? null);
        setFileContents(nextContents);
        setLegacyCode(loadedSession.latest_code ?? loadedSession.scenario.starter_code);
        setNotes(loadedSession.notes ?? "");
        setLastSavedAt(loadedWorkspace.last_autosaved_at ?? loadedSession.last_autosaved_at);
        setSubmission(loadedSession.submission);
        setCopilotMessages(loadedSession.ai_messages);

        if (!sessionStartedSent.current) {
          sessionStartedSent.current = true;
          void saveSessionEvent(token, loadedSession.id, { event_type: "session_started" }).catch(() => undefined);
        }
      })
      .catch((requestError: unknown) => {
        const message = requestError instanceof ApiError ? requestError.message : "Unable to load interview session.";
        setError(message);
      })
      .finally(() => setIsLoading(false));
  }, [params.sessionId, token]);

  useEffect(() => {
    if (!session?.started_at) {
      return;
    }

    const startedAt = new Date(session.started_at).getTime();
    const updateElapsedTime = () => {
      const nextElapsedSeconds = Math.max(0, Math.floor((new Date().getTime() - startedAt) / 1000));
      setElapsedSeconds(nextElapsedSeconds);
    };
    updateElapsedTime();
    const interval = window.setInterval(updateElapsedTime, 1000);
    return () => window.clearInterval(interval);
  }, [session?.started_at]);

  useEffect(() => {
    return () => {
      if (legacyCodeSaveTimer.current) {
        window.clearTimeout(legacyCodeSaveTimer.current);
      }
      if (noteSaveTimer.current) {
        window.clearTimeout(noteSaveTimer.current);
      }
      Object.values(fileSaveTimers.current).forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  async function saveWorkspaceFile(fileId: string, content: string) {
    if (!token || !session || isSubmitted) {
      return null;
    }
    const file = workspaceFiles.find((workspaceFile) => workspaceFile.id === fileId);
    if (!file || !file.is_editable) {
      return null;
    }

    setSavingFileIds((current) => new Set(current).add(fileId));
    try {
      const savedFile = await updateWorkspaceFile(token, session.id, fileId, { content });
      latestFileContents.current = { ...latestFileContents.current, [fileId]: savedFile.current_content };
      setFileContents((current) => ({ ...current, [fileId]: savedFile.current_content }));
      setWorkspace((current) =>
        current
          ? {
              ...current,
              last_autosaved_at: savedFile.updated_at,
              files: current.files.map((workspaceFile) => (workspaceFile.id === fileId ? savedFile : workspaceFile)),
            }
          : current,
      );
      setDirtyFileIds((current) => {
        const next = new Set(current);
        next.delete(fileId);
        return next;
      });
      setLastSavedAt(savedFile.updated_at);
      setError(null);
      return savedFile;
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to save workspace file.";
      setError(message);
      return null;
    } finally {
      setSavingFileIds((current) => {
        const next = new Set(current);
        next.delete(fileId);
        return next;
      });
    }
  }

  function queueWorkspaceAutosave(fileId: string, nextContent: string) {
    if (!token || !session || isSubmitted) {
      return;
    }
    if (fileSaveTimers.current[fileId]) {
      window.clearTimeout(fileSaveTimers.current[fileId]);
    }
    setDirtyFileIds((current) => new Set(current).add(fileId));
    fileSaveTimers.current[fileId] = window.setTimeout(() => {
      void saveWorkspaceFile(fileId, latestFileContents.current[fileId] ?? nextContent);
    }, 900);
  }

  async function flushPendingWorkspaceSaves() {
    const pendingFileIds = Array.from(dirtyFileIds);
    pendingFileIds.forEach((fileId) => {
      if (fileSaveTimers.current[fileId]) {
        window.clearTimeout(fileSaveTimers.current[fileId]);
        delete fileSaveTimers.current[fileId];
      }
    });
    await Promise.all(
      pendingFileIds.map((fileId) => saveWorkspaceFile(fileId, latestFileContents.current[fileId] ?? "")),
    );
  }

  function queueLegacyCodeAutosave(nextCode: string) {
    if (!token || !session || isSubmitted) {
      return;
    }
    if (legacyCodeSaveTimer.current) {
      window.clearTimeout(legacyCodeSaveTimer.current);
    }
    setIsSavingCode(true);
    legacyCodeSaveTimer.current = window.setTimeout(() => {
      saveSessionEvent(token, session.id, { event_type: "code_edit", payload: { code: nextCode } })
        .then((event) => {
          setLastSavedAt(String(event.payload.autosaved_at ?? event.created_at));
          setError(null);
        })
        .catch((requestError: unknown) => {
          const message = requestError instanceof ApiError ? requestError.message : "Unable to autosave code.";
          setError(message);
        })
        .finally(() => setIsSavingCode(false));
    }, 900);
  }

  function queueNotesAutosave(nextNotes: string) {
    if (!token || !session || isSubmitted) {
      return;
    }
    if (noteSaveTimer.current) {
      window.clearTimeout(noteSaveTimer.current);
    }
    setIsSavingNotes(true);
    noteSaveTimer.current = window.setTimeout(() => {
      saveSessionEvent(token, session.id, { event_type: "note_updated", payload: { notes: nextNotes } })
        .then((event) => {
          setLastSavedAt(String(event.payload.autosaved_at ?? event.created_at));
          setError(null);
        })
        .catch((requestError: unknown) => {
          const message = requestError instanceof ApiError ? requestError.message : "Unable to autosave notes.";
          setError(message);
        })
        .finally(() => setIsSavingNotes(false));
    }, 900);
  }

  function handleEditorChange(value: string | undefined) {
    const nextValue = value ?? "";
    if (selectedFile) {
      if (!selectedFile.is_editable || isSubmitted) {
        return;
      }
      latestFileContents.current = { ...latestFileContents.current, [selectedFile.id]: nextValue };
      setFileContents((current) => ({ ...current, [selectedFile.id]: nextValue }));
      queueWorkspaceAutosave(selectedFile.id, nextValue);
      return;
    }

    setLegacyCode(nextValue);
    queueLegacyCodeAutosave(nextValue);
  }

  function handleNotesChange(value: string) {
    setNotes(value);
    queueNotesAutosave(value);
  }

  function handleSelectFile(file: WorkspaceFile) {
    setSelectedFileId(file.id);
    if (!token || !session || openedFileIds.current.has(file.id)) {
      return;
    }
    openedFileIds.current.add(file.id);
    void saveSessionEvent(token, session.id, {
      event_type: "file_opened",
      payload: { file_id: file.id, path: file.path },
    }).catch(() => undefined);
  }

  async function handleRunTests() {
    if (!token || !session) {
      return;
    }

    setIsRunningTests(true);
    setError(null);
    try {
      if (hasWorkspace) {
        await flushPendingWorkspaceSaves();
      }
      const result = await runSessionTests(token, session.id, hasWorkspace ? {} : { code: legacyCode });
      setTestRun(result);
      setLastSavedAt(new Date().toISOString());
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to run simulated tests.";
      setError(message);
    } finally {
      setIsRunningTests(false);
    }
  }

  async function handleSubmit() {
    if (!token || !session) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    if (legacyCodeSaveTimer.current) {
      window.clearTimeout(legacyCodeSaveTimer.current);
      setIsSavingCode(false);
    }
    if (noteSaveTimer.current) {
      window.clearTimeout(noteSaveTimer.current);
      setIsSavingNotes(false);
    }

    try {
      if (hasWorkspace) {
        await flushPendingWorkspaceSaves();
      }
      const submittedFiles = hasWorkspace
        ? workspaceFiles.map((file) => ({
            path: file.path,
            content: latestFileContents.current[file.id] ?? file.current_content,
            language: file.language,
            file_type: file.file_type,
          }))
        : undefined;
      const createdSubmission = await submitSessionSolution(token, session.id, {
        code: selectedFile ? latestFileContents.current[selectedFile.id] ?? selectedFile.current_content : legacyCode,
        notes,
        test_output: testRun?.output ?? null,
        submitted_files: submittedFiles,
      });
      setSubmission(createdSubmission);
      setSession({
        ...session,
        status: "submitted",
        submitted_at: createdSubmission.submitted_at,
        latest_code: createdSubmission.code,
        notes: createdSubmission.notes,
        submission: createdSubmission,
      });
      setLastSavedAt(createdSubmission.submitted_at);
      setDirtyFileIds(new Set());
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to submit final solution.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAskCopilot() {
    if (!token || !session || copilotQuestion.trim().length === 0) {
      return;
    }

    const question = copilotQuestion.trim();
    const codeContext = selectedFile
      ? `File: ${selectedFile.path}\n\n${latestFileContents.current[selectedFile.id] ?? selectedFile.current_content}`
      : legacyCode;
    setIsAskingCopilot(true);
    setError(null);
    try {
      const response = await askCandidateCopilot(token, session.id, { question, code: codeContext });
      setCopilotMessages((currentMessages) => [
        ...currentMessages,
        response.user_message,
        response.assistant_message,
      ]);
      setCopilotQuestion("");
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to ask the AI copilot.";
      setError(message);
    } finally {
      setIsAskingCopilot(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95 px-5 py-3">
        <div className="mx-auto flex max-w-[1800px] flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <Link className="text-sm font-semibold text-cyan-300 hover:text-cyan-200" href="/">
              Nexterview
            </Link>
            <h1 className="mt-1 truncate text-xl font-semibold tracking-tight">
              {session?.scenario.title ?? "Candidate interview room"}
            </h1>
            <p className="mt-1 text-sm text-slate-400">{user?.email}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-md border border-slate-700 px-3 py-2 font-mono text-slate-200">
              {formatDuration(elapsedSeconds)}
            </span>
            <span className="rounded-md border border-slate-700 px-3 py-2 text-slate-300">
              {session?.status ?? "loading"}
            </span>
            <span className="rounded-md border border-slate-700 px-3 py-2 text-slate-400">
              Saved {formatSavedAt(lastSavedAt)}
            </span>
            <Button disabled={isRunningTests || isSubmitted} onClick={() => void handleRunTests()} type="button">
              {isRunningTests ? "Running..." : "Run tests"}
            </Button>
            <Button
              disabled={
                isSubmitting ||
                isSubmitted ||
                (hasWorkspace ? workspaceFiles.length === 0 : legacyCode.trim().length === 0)
              }
              onClick={() => void handleSubmit()}
              type="button"
            >
              {isSubmitting ? "Submitting..." : isSubmitted ? "Submitted" : "Submit"}
            </Button>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-[1800px] gap-4 px-4 py-4 xl:h-[calc(100vh-94px)] xl:grid-cols-[280px_minmax(0,1fr)_380px]">
        {isLoading ? (
          <div className="xl:col-span-3 rounded-md border border-slate-800 bg-slate-900/70 p-6 text-slate-300">
            Loading interview workspace...
          </div>
        ) : null}

        {error ? (
          <p className="xl:col-span-3 rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        {session ? (
          <>
            <aside className="min-h-0 overflow-hidden rounded-md border border-slate-800 bg-slate-900/70">
              <div className="border-b border-slate-800 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Workspace</p>
                <h2 className="mt-1 truncate text-sm font-semibold text-slate-100">
                  {workspace?.project?.project_name ?? "Single-file task"}
                </h2>
                {workspace?.project ? (
                  <div className="mt-3 grid gap-1 text-xs leading-5 text-slate-400">
                    {workspace.project.install_command ? <span>Install: {workspace.project.install_command}</span> : null}
                    {workspace.project.run_command ? <span>Run: {workspace.project.run_command}</span> : null}
                    {workspace.project.test_command ? <span>Test: {workspace.project.test_command}</span> : null}
                  </div>
                ) : null}
              </div>
              <div className="max-h-[42rem] overflow-auto p-2 xl:max-h-none">
                {hasWorkspace ? (
                  <FileTree
                    dirtyFileIds={dirtyFileIds}
                    files={workspaceFiles}
                    onSelect={handleSelectFile}
                    savingFileIds={savingFileIds}
                    selectedFileId={selectedFileId}
                  />
                ) : (
                  <button
                    className="w-full rounded-md bg-cyan-950/70 px-2 py-2 text-left text-xs text-cyan-100"
                    onClick={() => setSelectedFileId(null)}
                    type="button"
                  >
                    starter-code.{languageForStack(session.interview.stack)}
                  </button>
                )}
              </div>
            </aside>

            <section className="grid min-h-[760px] grid-rows-[auto_minmax(420px,1fr)_minmax(220px,auto)] overflow-hidden rounded-md border border-slate-800 bg-slate-900/70 xl:min-h-0">
              <div className="flex flex-col gap-3 border-b border-slate-800 p-4 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Editor</p>
                  <p className="mt-1 truncate text-sm font-medium text-slate-200">
                    {selectedFile?.path ?? "starter-code"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {selectedFile
                      ? `${selectedFile.language} / ${selectedFile.file_type}${selectedFile.is_editable ? "" : " / read-only"}`
                      : languageForStack(session.interview.stack)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                  {selectedFile && dirtyFileIds.has(selectedFile.id) ? <span className="text-amber-300">Unsaved changes</span> : null}
                  {selectedFile && savingFileIds.has(selectedFile.id) ? <span className="text-cyan-300">Saving...</span> : null}
                  {!selectedFile && isSavingCode ? <span className="text-cyan-300">Saving...</span> : null}
                  {isSubmitted ? <span>Final submission locked</span> : null}
                </div>
              </div>
              <div className="min-h-0">
                <MonacoEditor
                  height="100%"
                  language={selectedFile ? monacoLanguage(selectedFile.language) : languageForStack(session.interview.stack)}
                  onChange={handleEditorChange}
                  options={{
                    automaticLayout: true,
                    fontSize: 13,
                    minimap: { enabled: false },
                    readOnly: isSubmitted || Boolean(selectedFile && !selectedFile.is_editable),
                    scrollBeyondLastLine: false,
                    wordWrap: "on",
                  }}
                  theme="vs-dark"
                  value={selectedEditorValue}
                />
              </div>
              <section className="grid gap-4 border-t border-slate-800 p-4 lg:grid-cols-2">
                <div className="min-w-0">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-slate-100">Run output</h3>
                    {testRun ? (
                      <span className={testRun.status === "passed" ? "text-xs text-emerald-300" : "text-xs text-amber-300"}>
                        {testRun.status}
                      </span>
                    ) : null}
                  </div>
                  {testRun ? (
                    <div className="mt-3 grid max-h-52 gap-2 overflow-auto pr-1">
                      <p className={testRun.status === "passed" ? "text-sm text-emerald-300" : "text-sm text-amber-300"}>
                        {testRun.output}
                      </p>
                      {testRun.cases.map((testCase) => (
                        <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm" key={testCase.name}>
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium text-slate-200">{testCase.name}</span>
                            <span className={testCase.status === "passed" ? "text-emerald-300" : "text-amber-300"}>
                              {testCase.status}
                            </span>
                          </div>
                          <p className="mt-1 text-slate-400">{testCase.details}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      Simulated checks use the current session file snapshots and the project test command.
                    </p>
                  )}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-slate-100">Validation</h3>
                  <p className="mt-3 max-h-52 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
                    {session.scenario.validation_instructions || "Use the provided project tests and summarize your verification."}
                  </p>
                </div>
              </section>
            </section>

            <aside className="grid min-h-0 gap-4 xl:grid-rows-[minmax(0,1fr)_auto]">
              <div className="grid min-h-0 gap-4 overflow-auto pr-1">
                <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Task</p>
                  <h2 className="mt-2 text-lg font-semibold">{session.interview.role_title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{session.scenario.candidate_task_summary}</p>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{session.scenario.business_context}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {session.interview.stack.map((item) => (
                      <span className="rounded-md bg-slate-950 px-2.5 py-1 text-xs text-slate-300" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                </section>

                <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                  <h3 className="text-sm font-semibold text-slate-100">Requirements</h3>
                  <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-300">
                    {session.scenario.technical_requirements.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <div className="mt-4 grid gap-3 text-sm leading-6 text-slate-300">
                    <p>
                      <span className="font-semibold text-slate-100">Bug:</span> {session.scenario.bug_description}
                    </p>
                    <p>
                      <span className="font-semibold text-slate-100">Feature:</span> {session.scenario.feature_request}
                    </p>
                  </div>
                </section>

                <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                  <h3 className="text-sm font-semibold text-slate-100">Expected behavior</h3>
                  <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-300">
                    {session.scenario.expected_behavior.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>

                <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                  <h3 className="text-sm font-semibold text-slate-100">Logs or bug report</h3>
                  <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-300">
                    {session.scenario.logs_or_bug_report}
                  </pre>
                </section>

                <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-slate-100">AI copilot</h3>
                    <span className="text-xs text-slate-500">{session.interview.allowed_ai_mode}</span>
                  </div>
                  <div className="mt-3 grid max-h-[360px] gap-3 overflow-auto pr-1">
                    {copilotMessages.length === 0 ? (
                      <div className="rounded-md border border-slate-800 bg-slate-950 p-3 text-sm leading-6 text-slate-300">
                        Ask for implementation help, debugging hypotheses, code review, or a validation plan.
                      </div>
                    ) : (
                      copilotMessages.map((message) => <CopilotMessage key={message.id} message={message} />)
                    )}
                  </div>
                  <textarea
                    className="mt-3 min-h-24 w-full resize-none rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500"
                    disabled={isAskingCopilot}
                    onChange={(event) => setCopilotQuestion(event.target.value)}
                    placeholder="Ask for a hint, patch, debugging plan, or edge-case review."
                    value={copilotQuestion}
                  />
                  <Button
                    className="mt-3 w-full"
                    disabled={isAskingCopilot || copilotQuestion.trim().length === 0}
                    onClick={() => void handleAskCopilot()}
                    type="button"
                  >
                    {isAskingCopilot ? "Asking..." : "Ask copilot"}
                  </Button>
                </section>
              </div>

              <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-slate-100">Root cause / notes</h3>
                  <span className="text-xs text-slate-500">{isSavingNotes ? "Saving..." : "Autosaved"}</span>
                </div>
                <textarea
                  className="mt-3 min-h-40 w-full resize-y rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-200 outline-none focus:border-cyan-500"
                  disabled={isSubmitted}
                  onChange={(event) => handleNotesChange(event.target.value)}
                  placeholder="Explain the root cause, tradeoffs, validation steps, and what you changed."
                  value={notes}
                />
                {submission ? (
                  <div className="mt-3 rounded-md border border-emerald-900/70 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200">
                    Submitted at {formatSavedAt(submission.submitted_at)}.
                  </div>
                ) : null}
              </section>
            </aside>
          </>
        ) : null}
      </section>
    </main>
  );
}

export default function CandidateSessionPage() {
  return (
    <ProtectedRoute>
      <CandidateSessionContent />
    </ProtectedRoute>
  );
}
