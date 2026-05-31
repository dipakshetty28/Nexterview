"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
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
  CopilotSuggestedFile,
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

function branchUrl(submission: Submission): string | null {
  if (!submission.repository_url || !submission.branch_name) {
    return null;
  }
  return `${submission.repository_url}/tree/${encodeURIComponent(submission.branch_name)}`;
}

function formatCopilotTestOutput(testRun: TestRunResult | null): string | null {
  if (!testRun) {
    return null;
  }
  const caseLines = testRun.cases.map((testCase) => `- ${testCase.name}: ${testCase.status} - ${testCase.details}`);
  return [`Status: ${testRun.status}`, `Output: ${testRun.output}`, ...caseLines].join("\n");
}

const COPILOT_UNAVAILABLE_MESSAGE =
  "AI assistant is temporarily unavailable. Continue solving manually or try again.";

function sanitizeCandidateText(value: string): string {
  return value
    .replace(/\b(OPENAI_API_KEY|GITHUB_TOKEN|JWT_SECRET|DATABASE_URL|REDIS_URL)\s*=\s*[^\s]+/gi, "$1=[redacted]")
    .replace(/\b(postgresql|postgres|redis):\/\/[^\s)]+/gi, "$1://[redacted]")
    .replace(/\bsk-[A-Za-z0-9_-]{16,}/g, "sk-[redacted]")
    .replace(/\bgpt-[A-Za-z0-9_.-]+/gi, "[model]")
    .replace(/https:\/\/github\.com\/[^\s)]+\/(?:pull|tree|commit)\/[^\s)]+/gi, "[review link hidden]")
    .replace(/Traceback \(most recent call last\):[\s\S]*?(?=\n\n|$)/g, "[technical details hidden]")
    .replace(/^File ".+", line \d+,.+$/gm, "[technical details hidden]");
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
    const codeText = sanitizeCandidateText(String(children ?? "").replace(/\n$/, ""));
    if (!match) {
      return (
        <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[0.85em] text-cyan-200" {...props}>
          {sanitizeCandidateText(String(children ?? ""))}
        </code>
      );
    }

    return <CodeBlockWithCopy code={codeText} language={match[1]} />;
  },
  p({ children }) {
    return <p className="leading-6 text-slate-200">{children}</p>;
  },
  ul({ children }) {
    return <ul className="ml-4 list-disc space-y-1.5 leading-6 text-slate-200">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="ml-4 list-decimal space-y-1.5 leading-6 text-slate-200">{children}</ol>;
  },
  h1({ children }) {
    return <h1 className="text-base font-semibold text-slate-50">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="text-sm font-semibold text-slate-50">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-sm font-semibold text-slate-100">{children}</h3>;
  },
  blockquote({ children }) {
    return <blockquote className="border-l-2 border-cyan-700 pl-3 text-slate-300">{children}</blockquote>;
  },
};

function CodeBlockWithCopy({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="my-3 overflow-hidden rounded-md border border-slate-800 bg-slate-950">
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-3 py-2 text-xs text-slate-400">
        <span className="font-mono uppercase tracking-wide">{language}</span>
        <button
          className="rounded px-2 py-1 text-cyan-300 outline-none hover:bg-slate-800 hover:text-cyan-100 focus-visible:ring-2 focus-visible:ring-cyan-400/60"
          onClick={() => void handleCopy()}
          type="button"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="max-h-96 overflow-auto p-3 font-mono text-xs leading-5 text-slate-200">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function suggestedFilesForMessage(message: AIMessage): CopilotSuggestedFile[] {
  const rawSuggestedFiles = message.message_metadata?.suggested_files;
  if (!Array.isArray(rawSuggestedFiles)) {
    return [];
  }
  return rawSuggestedFiles.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return [];
    }
    const candidate = item as Record<string, unknown>;
    return typeof candidate.path === "string" && typeof candidate.reason === "string"
      ? [{ path: candidate.path, reason: candidate.reason }]
      : [];
  });
}

function confidenceForMessage(message: AIMessage): string | null {
  const confidence = message.message_metadata?.confidence;
  return typeof confidence === "string" ? confidence : null;
}

function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="grid gap-2 text-sm">
      <ReactMarkdown components={markdownComponents}>{sanitizeCandidateText(content)}</ReactMarkdown>
    </div>
  );
}

function ChatMessageBubble({
  role,
  content,
  suggestedFiles = [],
  confidence = null,
  isPending = false,
  onOpenSuggestedFile,
}: {
  role: "user" | "assistant";
  content: string;
  suggestedFiles?: CopilotSuggestedFile[];
  confidence?: string | null;
  isPending?: boolean;
  onOpenSuggestedFile: (path: string) => void;
}) {
  const isAssistant = role === "assistant";
  return (
    <div
      className={
        isAssistant
          ? "rounded-md border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200 shadow-sm"
          : "ml-5 rounded-md border border-cyan-900/70 bg-cyan-950/40 p-3 text-sm text-cyan-50 shadow-sm"
      }
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{isAssistant ? "AI Copilot" : "You"}</p>
        {isPending ? <span className="text-xs text-cyan-300">sending</span> : null}
      </div>
      {isAssistant ? (
        <div className="grid gap-2">
          <MarkdownMessage content={content} />
          {suggestedFiles.length > 0 ? (
            <div className="flex flex-wrap gap-2 pt-1">
              {suggestedFiles.map((file) => (
                <button
                  className="max-w-full truncate rounded-full border border-cyan-900/70 bg-cyan-950/30 px-2.5 py-1 text-left text-xs text-cyan-100 outline-none hover:border-cyan-600 focus-visible:ring-2 focus-visible:ring-cyan-400/60"
                  key={file.path}
                  onClick={() => onOpenSuggestedFile(file.path)}
                  title={sanitizeCandidateText(file.reason)}
                  type="button"
                >
                  {file.path}
                </button>
              ))}
            </div>
          ) : null}
          {confidence ? <p className="text-xs text-slate-500">Confidence: {confidence}</p> : null}
        </div>
      ) : (
        <p className="whitespace-pre-wrap leading-6">{sanitizeCandidateText(content)}</p>
      )}
    </div>
  );
}

function CopilotMessage({
  message,
  onOpenSuggestedFile,
}: {
  message: AIMessage;
  onOpenSuggestedFile: (path: string) => void;
}) {
  const isAssistant = message.role === "assistant";
  return (
    <ChatMessageBubble
      confidence={isAssistant ? confidenceForMessage(message) : null}
      content={message.content}
      onOpenSuggestedFile={onOpenSuggestedFile}
      role={message.role}
      suggestedFiles={isAssistant ? suggestedFilesForMessage(message) : []}
    />
  );
}

function AiEmptyState() {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
      <p className="font-medium text-slate-100">Ask for debugging help, code review, test ideas, or tradeoff analysis.</p>
      <p className="mt-2 text-slate-400">
        AI assistance is allowed. Your validation, reasoning, and judgment are evaluated.
      </p>
    </div>
  );
}

function AiTypingIndicator() {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
      <span className="inline-flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-cyan-300" />
        AI copilot is reviewing your context...
      </span>
    </div>
  );
}

function AiErrorState({ onRetry, isRetrying }: { onRetry: () => void; isRetrying: boolean }) {
  return (
    <div className="rounded-md border border-amber-900/70 bg-amber-950/30 p-3 text-sm text-amber-100">
      <p>{COPILOT_UNAVAILABLE_MESSAGE}</p>
      <Button className="mt-3 h-9 px-3" disabled={isRetrying} onClick={onRetry} type="button" variant="secondary">
        {isRetrying ? "Retrying..." : "Retry last prompt"}
      </Button>
    </div>
  );
}

function PromptQualityHints() {
  const examples = [
    "Here is the failing test and the code path I suspect...",
    "Compare these two possible fixes and risks...",
    "What edge cases should I test?",
  ];

  return (
    <div className="mt-3 rounded-md border border-slate-800 bg-slate-950/70 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Stronger prompts include context</p>
      <ul className="mt-2 grid gap-1.5 text-xs leading-5 text-slate-400">
        {examples.map((example) => (
          <li key={example}>{example}</li>
        ))}
      </ul>
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
  const [testRunError, setTestRunError] = useState<string | null>(null);
  const [testRunStartedAt, setTestRunStartedAt] = useState<string | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [copilotMessages, setCopilotMessages] = useState<AIMessage[]>([]);
  const [copilotQuestion, setCopilotQuestion] = useState("");
  const [isAskingCopilot, setIsAskingCopilot] = useState(false);
  const [copilotError, setCopilotError] = useState<string | null>(null);
  const [lastCopilotQuestion, setLastCopilotQuestion] = useState<string | null>(null);
  const [pendingCopilotQuestion, setPendingCopilotQuestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState(false);
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false);
  const [isRunPanelMinimized, setIsRunPanelMinimized] = useState(false);
  const [runPanelHeight, setRunPanelHeight] = useState(220);
  const legacyCodeSaveTimer = useRef<number | null>(null);
  const noteSaveTimer = useRef<number | null>(null);
  const fileSaveTimers = useRef<Record<string, number>>({});
  const latestFileContents = useRef<Record<string, string>>({});
  const openedFileIds = useRef<Set<string>>(new Set());
  const sessionStartedSent = useRef(false);
  const copilotMessagesEndRef = useRef<HTMLDivElement | null>(null);

  const workspaceFiles = workspace?.files ?? [];
  const hasWorkspace = workspaceFiles.length > 0;
  const selectedFile = workspaceFiles.find((file) => file.id === selectedFileId) ?? null;
  const selectedEditorValue = selectedFile
    ? fileContents[selectedFile.id] ?? selectedFile.current_content
    : legacyCode;
  const isSubmitted = session?.status === "submitted" || session?.status === "reviewed";
  const workspaceGridClass = isLeftPanelCollapsed
    ? isRightPanelCollapsed
      ? "xl:grid-cols-[48px_minmax(0,1fr)_48px]"
      : "xl:grid-cols-[48px_minmax(0,1fr)_380px]"
    : isRightPanelCollapsed
      ? "xl:grid-cols-[280px_minmax(0,1fr)_48px]"
      : "xl:grid-cols-[280px_minmax(0,1fr)_380px]";
  const editorRows = isRunPanelMinimized
    ? "auto minmax(0,1fr) 56px"
    : `auto minmax(0,1fr) ${runPanelHeight}px`;

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
        setCopilotError(null);
        setLastCopilotQuestion(null);
        setPendingCopilotQuestion(null);

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

  useEffect(() => {
    copilotMessagesEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [copilotMessages.length, pendingCopilotQuestion, isAskingCopilot, copilotError]);

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

  function handleOpenSuggestedFile(path: string) {
    const file = workspaceFiles.find((workspaceFile) => workspaceFile.path === path);
    if (!file) {
      setError(`Copilot suggested ${path}, but that file is not visible in this workspace.`);
      return;
    }
    handleSelectFile(file);
  }

  function handleAddSelectedFileContext() {
    if (!selectedFile) {
      return;
    }
    setCopilotQuestion((current) => {
      const trimmed = current.trim();
      const addition = `Use the currently open file ${selectedFile.path} as context.`;
      return trimmed ? `${trimmed}\n\n${addition}` : addition;
    });
  }

  async function handleRunTests() {
    if (!token || !session) {
      return;
    }

    setIsRunningTests(true);
    setError(null);
    setTestRunError(null);
    setTestRunStartedAt(new Date().toISOString());
    try {
      if (hasWorkspace) {
        await flushPendingWorkspaceSaves();
      }
      const result = await runSessionTests(token, session.id, hasWorkspace ? {} : { code: legacyCode });
      setTestRun(result);
      setLastSavedAt(new Date().toISOString());
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to run workspace checks.";
      setTestRunError(message);
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

  async function handleAskCopilot(questionOverride?: string) {
    if (!token || !session || isAskingCopilot || isSubmitted) {
      return;
    }

    const question = (questionOverride ?? copilotQuestion).trim();
    if (question.length === 0) {
      return;
    }

    setIsAskingCopilot(true);
    setCopilotError(null);
    setLastCopilotQuestion(question);
    setPendingCopilotQuestion(question);
    setError(null);
    try {
      if (hasWorkspace) {
        await flushPendingWorkspaceSaves();
      }
      const currentFileContent = selectedFile
        ? latestFileContents.current[selectedFile.id] ?? selectedFile.current_content
        : legacyCode;
      const response = await askCandidateCopilot(token, session.id, {
        question,
        code: currentFileContent,
        current_file_path: selectedFile?.path ?? null,
        current_file_content: currentFileContent,
        latest_test_output: formatCopilotTestOutput(testRun),
        notes,
      });
      setCopilotMessages((currentMessages) => [
        ...currentMessages,
        response.user_message,
        response.assistant_message,
      ]);
      setCopilotQuestion("");
    } catch {
      setCopilotError(COPILOT_UNAVAILABLE_MESSAGE);
    } finally {
      setIsAskingCopilot(false);
      setPendingCopilotQuestion(null);
    }
  }

  function handleCopilotKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    void handleAskCopilot();
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
              {isRunningTests ? "Running..." : "Run checks"}
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

      <section className={`mx-auto grid max-w-[1800px] gap-4 px-4 py-4 xl:h-[calc(100vh-94px)] ${workspaceGridClass}`}>
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
              {isLeftPanelCollapsed ? (
                <button
                  className="flex h-full min-h-16 w-full items-start justify-center px-2 py-4 text-xs font-semibold text-slate-300 hover:bg-slate-900"
                  onClick={() => setIsLeftPanelCollapsed(false)}
                  type="button"
                >
                  Files
                </button>
              ) : (
                <>
                  <div className="border-b border-slate-800 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Workspace</p>
                        <h2 className="mt-1 truncate text-sm font-semibold text-slate-100">
                          {workspace?.project?.project_name ?? "Single-file task"}
                        </h2>
                      </div>
                      <Button onClick={() => setIsLeftPanelCollapsed(true)} type="button" variant="secondary">
                        Hide
                      </Button>
                    </div>
                    {workspace?.project ? (
                      <div className="mt-3 grid gap-1 text-xs leading-5 text-slate-400">
                        <span>Environment ready</span>
                        <span>Dependencies pre-installed</span>
                        <span>Use Run checks for pass/fail feedback</span>
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
                </>
              )}
            </aside>

            <section
              className="grid min-h-[760px] overflow-hidden rounded-md border border-slate-800 bg-slate-900/70 xl:min-h-0"
              style={{ gridTemplateRows: editorRows }}
            >
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
              <section className="min-h-0 overflow-hidden border-t border-slate-800 bg-slate-950/70">
                {isRunPanelMinimized ? (
                  <div className="flex h-full items-center justify-between gap-3 px-4 py-2">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-slate-100">Run output</h3>
                      <p className="truncate text-xs text-slate-500">
                        {testRun ? testRun.output : "Panel minimized"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button disabled={isRunningTests || isSubmitted} onClick={() => void handleRunTests()} type="button">
                        {isRunningTests ? "Running..." : "Run checks"}
                      </Button>
                      <Button onClick={() => setIsRunPanelMinimized(false)} type="button" variant="secondary">
                        Show
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="grid h-full gap-4 overflow-auto p-4 lg:grid-cols-2">
                <div className="min-w-0">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">Workspace checks</h3>
                      <p className="mt-1 text-xs text-slate-500">
                        Pre-provisioned environment, current files, visible tests, and seed data
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {testRun ? (
                        <span className={testRun.status === "passed" ? "text-xs text-emerald-300" : "text-xs text-amber-300"}>
                          {testRun.status}
                        </span>
                      ) : null}
                      <label className="hidden items-center gap-2 text-xs text-slate-500 sm:flex">
                        <span>Height</span>
                        <input
                          className="h-1 w-24 accent-cyan-400"
                          max={420}
                          min={160}
                          onChange={(event) => setRunPanelHeight(Number(event.target.value))}
                          type="range"
                          value={runPanelHeight}
                        />
                      </label>
                      <Button disabled={isRunningTests || isSubmitted} onClick={() => void handleRunTests()} type="button">
                        {isRunningTests ? "Running..." : "Run checks"}
                      </Button>
                      <Button onClick={() => setIsRunPanelMinimized(true)} type="button" variant="secondary">
                        Minimize
                      </Button>
                    </div>
                  </div>
                  {isRunningTests ? (
                    <div className="mt-3 rounded-md border border-cyan-900/70 bg-cyan-950/20 px-3 py-2 text-sm text-cyan-100">
                      Checking the current workspace in the pre-provisioned environment
                      {testRunStartedAt ? `, started ${formatSavedAt(testRunStartedAt)}` : ""}.
                    </div>
                  ) : null}
                  {testRunError ? (
                    <div className="mt-3 rounded-md border border-red-900/70 bg-red-950/40 px-3 py-2 text-sm text-red-200">
                      {testRunError}
                    </div>
                  ) : null}
                  {testRun ? (
                    <div className="mt-3 grid max-h-56 gap-2 overflow-auto pr-1">
                      <div className={testRun.status === "passed" ? "rounded-md border border-emerald-900/70 bg-emerald-950/20 px-3 py-2 text-sm text-emerald-200" : "rounded-md border border-amber-900/70 bg-amber-950/20 px-3 py-2 text-sm text-amber-200"}>
                        {testRun.output}
                      </div>
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
                  ) : !isRunningTests && !testRunError ? (
                    <div className="mt-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-400">
                      Press Run checks to see which workspace test cases pass or fail against your current file snapshots.
                    </div>
                  ) : null}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-slate-100">Validation</h3>
                  <p className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-300">
                    {session.scenario.validation_instructions || "Use the provided project tests and summarize your verification."}
                  </p>
                </div>
                </div>
                )}
              </section>
            </section>

            <aside className="grid min-h-0 gap-4 xl:grid-rows-[minmax(0,1fr)_auto]">
              {isRightPanelCollapsed ? (
                <button
                  className="flex h-full min-h-16 w-full items-start justify-center rounded-md border border-slate-800 bg-slate-900/70 px-2 py-4 text-xs font-semibold text-slate-300 hover:bg-slate-900"
                  onClick={() => setIsRightPanelCollapsed(false)}
                  type="button"
                >
                  Task
                </button>
              ) : (
                <>
              <div className="grid min-h-0 gap-4 overflow-auto pr-1">
                <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Task</p>
                    <Button onClick={() => setIsRightPanelCollapsed(true)} type="button" variant="secondary">
                      Hide
                    </Button>
                  </div>
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

                <section className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/70">
                  <div className="border-b border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-slate-500">AI copilot</p>
                        <h3 className="mt-1 text-sm font-semibold text-slate-100">{session.interview.allowed_ai_mode}</h3>
                      </div>
                      <span className="rounded-full border border-cyan-900/70 bg-cyan-950/30 px-2.5 py-1 text-xs text-cyan-100">
                        Allowed
                      </span>
                    </div>
                    <p className="mt-3 text-xs leading-5 text-slate-400">
                      AI assistance is allowed. Your validation, reasoning, and judgment are evaluated.
                    </p>
                  </div>

                  <div className="grid max-h-[430px] gap-3 overflow-auto p-4 pr-2" aria-live="polite">
                    {copilotMessages.length === 0 && !pendingCopilotQuestion && !isAskingCopilot && !copilotError ? (
                      <AiEmptyState />
                    ) : null}
                    {copilotMessages.map((message) => (
                      <CopilotMessage
                        key={message.id}
                        message={message}
                        onOpenSuggestedFile={handleOpenSuggestedFile}
                      />
                    ))}
                    {pendingCopilotQuestion ? (
                      <ChatMessageBubble
                        content={pendingCopilotQuestion}
                        isPending
                        onOpenSuggestedFile={handleOpenSuggestedFile}
                        role="user"
                      />
                    ) : null}
                    {isAskingCopilot ? <AiTypingIndicator /> : null}
                    {copilotError ? (
                      <AiErrorState
                        isRetrying={isAskingCopilot}
                        onRetry={() => void handleAskCopilot(lastCopilotQuestion ?? copilotQuestion)}
                      />
                    ) : null}
                    <div ref={copilotMessagesEndRef} />
                  </div>

                  <div className="border-t border-slate-800 p-4">
                    <label className="grid gap-2 text-sm text-slate-200">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Prompt</span>
                      <textarea
                        className="min-h-24 w-full resize-none rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-200 outline-none transition placeholder:text-slate-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
                        disabled={isAskingCopilot || isSubmitted}
                        onChange={(event) => {
                          setCopilotQuestion(event.target.value);
                          setCopilotError(null);
                        }}
                        onKeyDown={handleCopilotKeyDown}
                        placeholder="Ask for a hint, patch, debugging plan, or edge-case review."
                        value={copilotQuestion}
                      />
                    </label>
                    <PromptQualityHints />
                    <div className="mt-3 grid gap-2">
                      {selectedFile ? (
                        <Button
                          className="w-full"
                          disabled={isAskingCopilot || isSubmitted}
                          onClick={handleAddSelectedFileContext}
                          type="button"
                          variant="secondary"
                        >
                          Add selected file context
                        </Button>
                      ) : null}
                      <Button
                        className="w-full"
                        disabled={isAskingCopilot || isSubmitted || copilotQuestion.trim().length === 0}
                        onClick={() => void handleAskCopilot()}
                        type="button"
                      >
                        {isAskingCopilot ? "Sending..." : "Send"}
                      </Button>
                    </div>
                  </div>
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
                  <div className="mt-3 grid gap-2 rounded-md border border-emerald-900/70 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200">
                    <p>Submitted at {formatSavedAt(submission.submitted_at)}.</p>
                    {submission.push_status === "pushed" ? (
                      <div className="grid gap-1 text-emerald-100">
                        {branchUrl(submission) ? (
                          <a className="font-medium text-cyan-200 hover:text-cyan-100" href={branchUrl(submission) ?? ""}>
                            Branch created: {submission.branch_name}
                          </a>
                        ) : (
                          <p>Branch created: {submission.branch_name}</p>
                        )}
                        {submission.pull_request_url ? (
                          <a className="font-medium text-cyan-200 hover:text-cyan-100" href={submission.pull_request_url}>
                            Open pull request
                          </a>
                        ) : null}
                      </div>
                    ) : null}
                    {submission.push_status === "not_configured" ? (
                      <p className="text-emerald-100">GitHub push is disabled. Your submitted files were saved in Nexterview.</p>
                    ) : null}
                    {submission.push_status === "failed" ? (
                      <p className="text-amber-200">
                        GitHub push failed, but your submitted files were saved in Nexterview.
                      </p>
                    ) : null}
                    {submission.push_status === "no_changes" ? (
                      <p className="text-emerald-100">No changed files were detected for GitHub, so Nexterview saved the submission only.</p>
                    ) : null}
                  </div>
                ) : null}
              </section>
                </>
              )}
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
