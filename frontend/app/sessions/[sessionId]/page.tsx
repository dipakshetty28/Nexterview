"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  type RefObject,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { Panel, PanelGroup, PanelResizeHandle, type ImperativePanelHandle } from "react-resizable-panels";

import { CoachMark } from "@/components/app/coach-mark";
import { useAuth } from "@/components/auth/auth-provider";
import { ProtectedRoute } from "@/components/auth/protected-route";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
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
      Preparing editor
    </div>
  ),
});

type TreeNode = {
  name: string;
  path: string;
  children: TreeNode[];
  file?: WorkspaceFile;
};

type WorkspacePanelId = "task" | "editor" | "copilot" | "output";

type MonacoEditorHandle = {
  layout: () => void;
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
          isSelected ? "bg-blue-600 text-white shadow-sm" : "text-slate-300 hover:bg-slate-800"
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
        className="cursor-pointer rounded-md px-2 py-1.5 text-xs font-semibold text-slate-400 hover:bg-slate-800"
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
  isPending = false,
  onOpenSuggestedFile,
}: {
  role: "user" | "assistant";
  content: string;
  suggestedFiles?: CopilotSuggestedFile[];
  isPending?: boolean;
  onOpenSuggestedFile: (path: string) => void;
}) {
  const isAssistant = role === "assistant";
  return (
    <div
      className={
        isAssistant
          ? "rounded-lg border border-slate-700 bg-slate-800/80 p-3 text-sm text-slate-200 shadow-sm"
          : "ml-5 rounded-lg border border-blue-800 bg-blue-950/50 p-3 text-sm text-blue-50 shadow-sm"
      }
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{isAssistant ? "AI Copilot" : "You"}</p>
        {isPending ? <span className="text-xs text-blue-300">sending</span> : null}
      </div>
      {isAssistant ? (
        <div className="grid gap-2">
          <MarkdownMessage content={content} />
          {suggestedFiles.length > 0 ? (
            <div className="flex flex-wrap gap-2 pt-1">
              {suggestedFiles.map((file) => (
                <button
                  className="max-w-full truncate rounded-full border border-blue-800 bg-blue-950/40 px-2.5 py-1 text-left text-xs text-blue-100 outline-none hover:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-400/60"
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
      content={message.content}
      onOpenSuggestedFile={onOpenSuggestedFile}
      role={message.role}
      suggestedFiles={isAssistant ? suggestedFilesForMessage(message) : []}
    />
  );
}

function AiEmptyState() {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/70 p-4 text-sm leading-6 text-slate-300">
      <p className="font-medium text-slate-100">Ask for debugging help, code review, test ideas, or tradeoff analysis.</p>
    </div>
  );
}

function AiTypingIndicator() {
  return (
    <div className="rounded-lg border border-blue-900/70 bg-blue-950/25 p-3 text-sm text-blue-100">
      <span className="inline-flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-blue-300" />
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

function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "success" | "warning" | "danger" }) {
  const toneClass = {
    neutral: "border-slate-600 bg-slate-800 text-slate-100",
    success: "border-emerald-700 bg-emerald-950/80 text-emerald-200",
    warning: "border-amber-700 bg-amber-950/80 text-amber-200",
    danger: "border-red-700 bg-red-950/80 text-red-200",
  }[tone];

  return (
    <span className={cn("inline-flex h-7 items-center rounded-full border px-2.5 text-xs font-semibold shadow-sm", toneClass)}>
      {label}
    </span>
  );
}

function WorkspaceLoadingState() {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/80 p-5" role="status" aria-live="polite">
      <div className="flex items-center gap-3">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-cyan-300" />
        <span className="text-sm font-medium text-slate-200">Preparing interview workspace</span>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="h-40 animate-pulse rounded-md bg-slate-950/80" />
        <div className="h-40 animate-pulse rounded-md bg-slate-950/80 md:col-span-2" />
      </div>
    </div>
  );
}

function PanelIconButton({
  label,
  icon,
  disabled = false,
  onClick,
}: {
  label: string;
  icon: "minimize" | "maximize" | "restore";
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      className="relative inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-700 bg-slate-900 text-slate-400 outline-none transition hover:border-slate-500 hover:bg-slate-800 hover:text-white focus-visible:ring-2 focus-visible:ring-blue-400/60 disabled:cursor-not-allowed disabled:opacity-35"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {icon === "minimize" ? <span className="h-px w-3 bg-current" /> : null}
      {icon === "maximize" ? <span className="h-3 w-3 rounded-[2px] border border-current" /> : null}
      {icon === "restore" ? (
        <span className="relative h-3.5 w-3.5">
          <span className="absolute right-0 top-0 h-2.5 w-2.5 rounded-[2px] border border-current" />
          <span className="absolute bottom-0 left-0 h-2.5 w-2.5 rounded-[2px] border border-current bg-slate-900" />
        </span>
      ) : null}
    </button>
  );
}

function PanelHeader({
  title,
  eyebrow,
  meta,
  panelId,
  isMaximized,
  onMinimize,
  onMaximize,
  onRestore,
  actions,
}: {
  title: string;
  eyebrow?: string;
  meta?: string;
  panelId: WorkspacePanelId;
  isMaximized: boolean;
  onMinimize: (panelId: WorkspacePanelId) => void;
  onMaximize: (panelId: WorkspacePanelId) => void;
  onRestore: () => void;
  actions?: ReactNode;
}) {
  return (
    <div className="flex min-h-14 items-center justify-between gap-3 border-b border-slate-700/80 bg-slate-900 px-3 py-2 shadow-sm">
      <div className="min-w-0">
        {eyebrow ? <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-300">{eyebrow}</p> : null}
        <h2 className="truncate text-sm font-semibold text-white">{title}</h2>
        {meta ? <p className="truncate text-xs text-slate-400">{meta}</p> : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {actions}
        <PanelIconButton icon="minimize" label={`Minimize ${title} panel`} onClick={() => onMinimize(panelId)} />
        <PanelIconButton icon="maximize" label={`Maximize ${title} panel`} onClick={() => onMaximize(panelId)} />
        <PanelIconButton disabled={!isMaximized} icon="restore" label={`Restore ${title} panel`} onClick={onRestore} />
      </div>
    </div>
  );
}

function IdePanel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={cn(
        "flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-slate-700/80 bg-slate-900 shadow-[0_18px_45px_rgba(15,23,42,0.28),0_2px_8px_rgba(15,23,42,0.2)]",
        className,
      )}
    >
      {children}
    </section>
  );
}

function CollapsedPanelRestore({
  label,
  orientation = "vertical",
  onRestore,
}: {
  label: string;
  orientation?: "vertical" | "horizontal";
  onRestore: () => void;
}) {
  return (
    <button
      aria-label={`Restore ${label} panel`}
      className="flex h-full w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-xs font-semibold uppercase tracking-wide text-slate-300 shadow-lg outline-none transition hover:border-blue-500 hover:bg-slate-800 hover:text-blue-200 focus-visible:ring-2 focus-visible:ring-blue-400/60"
      onClick={onRestore}
      type="button"
    >
      <span className={orientation === "vertical" ? "[writing-mode:vertical-rl]" : ""}>{label}</span>
    </button>
  );
}

function ResizeGrip({ orientation }: { orientation: "vertical" | "horizontal" }) {
  return (
    <PanelResizeHandle
      aria-label={orientation === "vertical" ? "Resize workspace columns" : "Resize output panel"}
      className={cn(
        "group flex items-center justify-center rounded outline-none transition focus-visible:ring-2 focus-visible:ring-blue-400/60",
        orientation === "vertical" ? "w-3 cursor-col-resize px-1" : "h-3 cursor-row-resize py-1",
      )}
    >
      <span
        className={cn(
          "rounded-full bg-slate-400/70 shadow-sm transition group-hover:bg-blue-500 group-data-[resize-handle-active]:bg-blue-400",
          orientation === "vertical" ? "h-16 w-1" : "h-1 w-16",
        )}
      />
    </PanelResizeHandle>
  );
}

function TaskPanel({ session }: { session: CandidateSession }) {
  const scenario = session.scenario;
  const requirements = scenario.visible_requirements.length ? scenario.visible_requirements : scenario.technical_requirements;

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-slate-900 px-4 py-4">
      <div className="grid gap-4">
        <section className="rounded-lg border border-slate-700 bg-slate-800/80 p-4 shadow-sm">
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={sanitizeCandidateText(scenario.language || "Language")} />
            {scenario.framework ? <StatusBadge label={sanitizeCandidateText(scenario.framework)} /> : null}
          </div>
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-white">{scenario.title}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-300">{scenario.business_context}</p>
        </section>

        {scenario.candidate_instructions ? (
          <section className="rounded-lg border border-blue-900/70 bg-blue-950/30 p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-blue-300">Assignment brief</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-200">
              {sanitizeCandidateText(scenario.candidate_instructions)}
            </p>
          </section>
        ) : null}

        <section className="rounded-lg border border-slate-700 bg-slate-800/55 p-4">
          <h2 className="text-sm font-semibold text-white">Requirements</h2>
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-200">
            {requirements.map((item) => (
              <li className="grid grid-cols-[18px_1fr] gap-2 rounded-md border border-slate-700 bg-slate-900/70 px-3 py-2" key={item}>
                <span aria-hidden="true" className="mt-1 h-3.5 w-3.5 rounded border border-blue-400 bg-blue-950" />
                <span>{sanitizeCandidateText(item)}</span>
              </li>
            ))}
          </ul>
        </section>

        {scenario.constraints.length ? (
          <section className="rounded-lg border border-slate-700 bg-slate-800/55 p-4">
            <h2 className="text-sm font-semibold text-white">Constraints</h2>
            <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-300">
              {scenario.constraints.map((item) => (
                <li className="border-l-2 border-amber-500 pl-3" key={item}>
                  {sanitizeCandidateText(item)}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="rounded-lg border border-slate-700 bg-slate-800/55 p-4">
          <h2 className="text-sm font-semibold text-white">Expected deliverables</h2>
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-slate-300">
            {scenario.expected_behavior.map((item) => (
              <li className="grid grid-cols-[6px_1fr] gap-3" key={item}>
                <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span>{sanitizeCandidateText(item)}</span>
              </li>
            ))}
          </ul>
        </section>

        {scenario.bug_description || scenario.feature_request ? (
          <section className="grid gap-3">
            {scenario.bug_description ? (
              <div className="rounded-lg border border-rose-900/70 bg-rose-950/25 p-4">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-rose-300">Issue to investigate</h2>
                <p className="mt-2 text-sm leading-6 text-slate-200">{sanitizeCandidateText(scenario.bug_description)}</p>
              </div>
            ) : null}
            {scenario.feature_request ? (
              <div className="rounded-lg border border-emerald-900/70 bg-emerald-950/25 p-4">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Requested behavior</h2>
                <p className="mt-2 text-sm leading-6 text-slate-200">{sanitizeCandidateText(scenario.feature_request)}</p>
              </div>
            ) : null}
          </section>
        ) : null}

        {scenario.logs_or_bug_report ? (
          <section className="rounded-lg border border-slate-700 bg-slate-950 p-4">
            <h2 className="text-sm font-semibold text-white">Logs or bug report</h2>
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-black/30 p-3 font-mono text-xs leading-5 text-slate-300">
              {sanitizeCandidateText(scenario.logs_or_bug_report)}
            </pre>
          </section>
        ) : null}

        <section className="rounded-lg border border-slate-700 bg-slate-800/55 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-white">Validation</h2>
            {scenario.validation_command ? (
              <code className="rounded-full border border-blue-800 bg-blue-950/60 px-3 py-1 text-xs text-blue-200">
                {sanitizeCandidateText(scenario.validation_command)}
              </code>
            ) : null}
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {sanitizeCandidateText(
              scenario.validation_instructions ||
                "Run checks, fix the issue, implement the requested behavior, and summarize verification.",
            )}
          </p>
        </section>
      </div>
    </div>
  );
}

function OutputPanel({
  testRun,
  testRunError,
  testRunStartedAt,
  isRunningTests,
  isSubmitted,
  isSavingNotes,
  notes,
  submission,
  validationInstructions,
  validationCommand,
  onNotesChange,
  onRunTests,
}: {
  testRun: TestRunResult | null;
  testRunError: string | null;
  testRunStartedAt: string | null;
  isRunningTests: boolean;
  isSubmitted: boolean;
  isSavingNotes: boolean;
  notes: string;
  submission: Submission | null;
  validationInstructions: string;
  validationCommand: string;
  onNotesChange: (value: string) => void;
  onRunTests: () => void;
}) {
  return (
    <div className="grid h-full min-h-0 gap-4 overflow-auto bg-slate-900 p-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.65fr)]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Workspace checks</h3>
            <p className="mt-1 text-xs text-slate-500">
              Runs <span className="font-mono text-slate-300">{sanitizeCandidateText(validationCommand || "workspace checks")}</span> against the current saved files.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {testRun ? (
              <StatusBadge
                label={testRun.status === "passed" ? "Passed" : testRun.status}
                tone={testRun.status === "passed" ? "success" : testRun.status === "failed" ? "warning" : "danger"}
              />
            ) : null}
            <Button className="h-9 px-3" disabled={isRunningTests || isSubmitted} onClick={onRunTests} type="button">
              {isRunningTests ? "Running..." : "Run checks"}
            </Button>
          </div>
        </div>

        {isRunningTests ? (
          <div className="mt-3 rounded border border-cyan-900/70 bg-cyan-950/20 px-3 py-2 text-sm text-cyan-100">
            Checking the current workspace{testRunStartedAt ? `, started ${formatSavedAt(testRunStartedAt)}` : ""}.
          </div>
        ) : null}

        {testRunError ? (
          <div className="mt-3 rounded border border-red-900/70 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            {sanitizeCandidateText(testRunError)}
          </div>
        ) : null}

        {testRun ? (
          <div className="mt-3 grid gap-3">
            <div className="grid gap-2 rounded-lg border border-slate-700 bg-slate-800/70 px-3 py-3 text-xs text-slate-300 sm:grid-cols-4">
              <span>
                Command <span className="block font-mono text-slate-100">{sanitizeCandidateText(testRun.command)}</span>
              </span>
              <span>
                Result <span className="block font-semibold text-slate-100">{testRun.status}</span>
              </span>
              <span>
                Passed <span className="block font-semibold text-emerald-200">{testRun.passed_count}/{testRun.total_count}</span>
              </span>
              <span>
                Duration <span className="block font-semibold text-slate-100">{testRun.duration_ms}ms</span>
              </span>
            </div>
            {testRun.failure_summary ? (
              <div className="rounded border border-amber-900/70 bg-amber-950/20 px-3 py-2 text-sm text-amber-100">
                {sanitizeCandidateText(testRun.failure_summary)}
              </div>
            ) : null}
            {testRun.output ? (
              <section>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Runner output</p>
                <pre
                  className={cn(
                    "max-h-32 overflow-auto whitespace-pre-wrap rounded-lg border px-3 py-2 font-mono text-xs leading-5",
                    testRun.status === "passed"
                      ? "border-emerald-900/70 bg-emerald-950/20 text-emerald-100"
                      : "border-amber-900/70 bg-amber-950/20 text-amber-100",
                  )}
                >
                  {sanitizeCandidateText(testRun.output)}
                </pre>
              </section>
            ) : null}
            {testRun.stdout ? (
              <section>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Standard output</p>
                <pre className="max-h-44 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 font-mono text-xs leading-5 text-slate-300">
                  {sanitizeCandidateText(testRun.stdout)}
                </pre>
              </section>
            ) : null}
            {testRun.stderr ? (
              <section>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-rose-400">Standard error</p>
                <pre className="max-h-36 overflow-auto whitespace-pre-wrap rounded-lg border border-red-900/60 bg-red-950/20 px-3 py-2 font-mono text-xs leading-5 text-red-100">
                  {sanitizeCandidateText(testRun.stderr)}
                </pre>
              </section>
            ) : null}
            <div className="grid max-h-56 gap-2 overflow-auto pr-1">
              {testRun.cases.map((testCase) => (
                <div className="rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm" key={testCase.name}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="min-w-0 truncate font-medium text-slate-200">{sanitizeCandidateText(testCase.name)}</span>
                    <StatusBadge
                      label={testCase.status === "passed" ? "Pass" : "Fail"}
                      tone={testCase.status === "passed" ? "success" : "warning"}
                    />
                  </div>
                  <p className="mt-1 text-slate-400">{sanitizeCandidateText(testCase.details)}</p>
                </div>
              ))}
            </div>
          </div>
        ) : !isRunningTests && !testRunError ? (
          <div className="mt-3 rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-400">
            Tests have not been run yet. Run checks when you want pass/fail feedback for the current workspace.
          </div>
        ) : null}
      </div>

      <div className="min-w-0 rounded-lg border border-slate-700 bg-slate-800/55 p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-white">Final explanation</h3>
          <span className="text-xs text-slate-500">{isSavingNotes ? "Saving..." : "Required"}</span>
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-400">
          Summarize the root cause, changes, tradeoffs, and how you validated the result.
        </p>
        <textarea
          className="mt-3 min-h-40 w-full resize-y rounded-lg border border-slate-600 bg-slate-950 px-3 py-3 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600 focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-400/40 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitted}
          id="candidate-notes"
          onChange={(event) => onNotesChange(event.target.value)}
          placeholder="Explain your diagnosis, implementation, tradeoffs, and validation."
          value={notes}
        />
        {!notes.trim() && !isSubmitted ? (
          <p className="mt-2 text-xs text-amber-300">A final explanation is required before submission.</p>
        ) : null}
        {submission ? (
          <div className="mt-3 rounded-lg border border-emerald-900/70 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-100">
            Submitted {formatSavedAt(submission.submitted_at)}. The workspace is locked for review.
          </div>
        ) : null}

        <div className="mt-4 border-t border-slate-700 pt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Validation guidance</h4>
            {testRun ? <span className="text-xs text-slate-500">Last run {formatSavedAt(testRun.created_at)}</span> : null}
          </div>
          {validationCommand ? (
            <code className="mt-3 block w-fit max-w-full truncate rounded-full border border-blue-800 bg-blue-950/50 px-3 py-1 text-xs text-blue-200">
              {sanitizeCandidateText(validationCommand)}
            </code>
          ) : null}
          <p className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {sanitizeCandidateText(validationInstructions || "Use the provided checks and summarize your verification before submitting.")}
          </p>
        </div>
      </div>
    </div>
  );
}

function SubmitConfirmDialog({
  isOpen,
  notes,
  isSubmitting,
  testRun,
  onCancel,
  onConfirm,
}: {
  isOpen: boolean;
  notes: string;
  isSubmitting: boolean;
  testRun: TestRunResult | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onCancel();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
      <div
        aria-modal="true"
        className="w-full max-w-xl overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl shadow-slate-950"
        role="dialog"
      >
        <div className="border-b border-slate-700 bg-slate-800/80 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Final submission</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Submit and lock this workspace?</h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Your saved files and final explanation will be submitted for interviewer review. You will not be able to edit
            the workspace after this.
          </p>
        </div>
        <div className="grid gap-4 p-5">
          {!testRun || testRun.status !== "passed" ? (
            <div className="rounded-lg border border-amber-800 bg-amber-950/35 p-3 text-sm leading-6 text-amber-100">
              {testRun
                ? `The latest test run is ${testRun.status}. You can still submit, but the interviewer will see the validation result.`
                : "No test run is recorded yet. You can still submit, but running tests first provides stronger validation evidence."}
            </div>
          ) : (
            <div className="flex items-center justify-between rounded-lg border border-emerald-800 bg-emerald-950/35 px-3 py-2">
              <span className="text-sm font-medium text-emerald-100">Latest test run passed</span>
              <StatusBadge label={`${testRun.passed_count}/${testRun.total_count} passed`} tone="success" />
            </div>
          )}
          <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Your final explanation</p>
            <p className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
              {sanitizeCandidateText(notes.trim())}
            </p>
          </div>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button className="h-10" disabled={isSubmitting} onClick={onCancel} type="button" variant="secondary">
              Keep editing
            </Button>
            <Button className="h-10" disabled={isSubmitting} onClick={onConfirm} type="button">
              {isSubmitting ? "Submitting..." : "Submit final solution"}
            </Button>
          </div>
        </div>
      </div>
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
  const [error, setError] = useState<string | null>(null);
  const [minimizedPanels, setMinimizedPanels] = useState<Set<WorkspacePanelId>>(new Set());
  const [maximizedPanel, setMaximizedPanel] = useState<WorkspacePanelId | null>(null);
  const [isSubmitDialogOpen, setIsSubmitDialogOpen] = useState(false);
  const [submitSuccessMessage, setSubmitSuccessMessage] = useState<string | null>(null);
  const [copilotError, setCopilotError] = useState<string | null>(null);
  const [lastCopilotQuestion, setLastCopilotQuestion] = useState<string | null>(null);
  const [pendingCopilotQuestion, setPendingCopilotQuestion] = useState<string | null>(null);
  const legacyCodeSaveTimer = useRef<number | null>(null);
  const noteSaveTimer = useRef<number | null>(null);
  const fileSaveTimers = useRef<Record<string, number>>({});
  const latestFileContents = useRef<Record<string, string>>({});
  const openedFileIds = useRef<Set<string>>(new Set());
  const sessionStartedSent = useRef(false);
  const taskPanelRef = useRef<ImperativePanelHandle>(null);
  const editorPanelRef = useRef<ImperativePanelHandle>(null);
  const copilotPanelRef = useRef<ImperativePanelHandle>(null);
  const outputPanelRef = useRef<ImperativePanelHandle>(null);
  const codePanelRef = useRef<ImperativePanelHandle>(null);
  const editorInstanceRef = useRef<MonacoEditorHandle | null>(null);
  const horizontalLayoutRef = useRef<number[]>([]);
  const editorLayoutRef = useRef<number[]>([]);
  const layoutBeforeMaximizeRef = useRef<{ horizontal: number[]; editor: number[] } | null>(null);
  const copilotMessagesEndRef = useRef<HTMLDivElement | null>(null);

  const workspaceFiles = workspace?.files ?? [];
  const hasWorkspace = workspaceFiles.length > 0;
  const selectedFile = workspaceFiles.find((file) => file.id === selectedFileId) ?? null;
  const selectedEditorValue = selectedFile
    ? fileContents[selectedFile.id] ?? selectedFile.current_content
    : legacyCode;
  const isSubmitted = Boolean(
    session?.status &&
      ["submitted", "ready_for_review", "review_in_progress", "reviewed", "review_failed"].includes(session.status),
  );
  const finalExplanation = notes.trim();
  const canSubmit =
    Boolean(session) &&
    !isSubmitting &&
    !isSubmitted &&
    finalExplanation.length > 0 &&
    (hasWorkspace ? workspaceFiles.length > 0 : legacyCode.trim().length > 0);

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
        setSubmitSuccessMessage(
          loadedSession.submission ? "Final solution submitted. The workspace is locked for review." : null,
        );

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
  }, [copilotMessages.length, copilotError, isAskingCopilot, pendingCopilotQuestion]);

  function requestEditorLayout() {
    window.requestAnimationFrame(() => {
      editorInstanceRef.current?.layout();
      window.setTimeout(() => editorInstanceRef.current?.layout(), 80);
    });
  }

  function handleHorizontalLayout(sizes: number[]) {
    horizontalLayoutRef.current = sizes;
    requestEditorLayout();
  }

  function handleEditorPanelLayout(sizes: number[]) {
    editorLayoutRef.current = sizes;
    requestEditorLayout();
  }

  function panelRefFor(panelId: WorkspacePanelId): RefObject<ImperativePanelHandle | null> {
    if (panelId === "task") {
      return taskPanelRef;
    }
    if (panelId === "editor") {
      return editorPanelRef;
    }
    if (panelId === "copilot") {
      return copilotPanelRef;
    }
    return outputPanelRef;
  }

  function handleMinimizePanel(panelId: WorkspacePanelId) {
    setMaximizedPanel(null);
    setMinimizedPanels((current) => new Set(current).add(panelId));
    panelRefFor(panelId).current?.collapse();
    requestEditorLayout();
  }

  function handleRestorePanel(panelId?: WorkspacePanelId) {
    const targetPanels: WorkspacePanelId[] = panelId ? [panelId] : ["task", "editor", "copilot", "output"];
    targetPanels.forEach((targetPanel) => panelRefFor(targetPanel).current?.expand());

    if (!panelId && layoutBeforeMaximizeRef.current) {
      const { horizontal, editor } = layoutBeforeMaximizeRef.current;
      window.setTimeout(() => {
        if (horizontal.length === 3) {
          taskPanelRef.current?.resize(horizontal[0]);
          editorPanelRef.current?.resize(horizontal[1]);
          copilotPanelRef.current?.resize(horizontal[2]);
        }
        if (editor.length === 2) {
          codePanelRef.current?.resize(editor[0]);
          outputPanelRef.current?.resize(editor[1]);
        }
        layoutBeforeMaximizeRef.current = null;
        requestEditorLayout();
      }, 0);
    }

    setMinimizedPanels((current) => {
      if (!panelId) {
        return new Set();
      }
      const next = new Set(current);
      next.delete(panelId);
      return next;
    });
    setMaximizedPanel(panelId ? maximizedPanel : null);
    if (panelId && maximizedPanel === panelId) {
      setMaximizedPanel(null);
    }
    requestEditorLayout();
  }

  function handleMaximizePanel(panelId: WorkspacePanelId) {
    if (!maximizedPanel) {
      layoutBeforeMaximizeRef.current = {
        horizontal: horizontalLayoutRef.current,
        editor: editorLayoutRef.current,
      };
    }

    setMinimizedPanels(new Set());
    setMaximizedPanel(panelId);
    ["task", "editor", "copilot", "output"].forEach((targetPanel) =>
      panelRefFor(targetPanel as WorkspacePanelId).current?.expand(),
    );

    window.setTimeout(() => {
      if (panelId === "task") {
        taskPanelRef.current?.resize(88);
        editorPanelRef.current?.resize(6);
        copilotPanelRef.current?.resize(6);
      }
      if (panelId === "editor") {
        taskPanelRef.current?.resize(6);
        editorPanelRef.current?.resize(88);
        copilotPanelRef.current?.resize(6);
        codePanelRef.current?.resize(72);
        outputPanelRef.current?.resize(28);
      }
      if (panelId === "copilot") {
        taskPanelRef.current?.resize(6);
        editorPanelRef.current?.resize(6);
        copilotPanelRef.current?.resize(88);
      }
      if (panelId === "output") {
        taskPanelRef.current?.resize(5);
        editorPanelRef.current?.resize(90);
        copilotPanelRef.current?.resize(5);
        codePanelRef.current?.resize(18);
        outputPanelRef.current?.resize(82);
      }
      requestEditorLayout();
    }, 0);
  }

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
    if (!token || !session || isSubmitting || isSubmitted || submission || finalExplanation.length === 0) {
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
        notes: finalExplanation,
        test_output: testRun?.output ?? null,
        submitted_files: submittedFiles,
      });
      setSubmission(createdSubmission);
      setSession({
        ...session,
        status: "submitted",
        submitted_at: createdSubmission.submitted_at,
        latest_code: createdSubmission.code,
        notes: finalExplanation,
        submission: createdSubmission,
      });
      setNotes(finalExplanation);
      setLastSavedAt(createdSubmission.submitted_at);
      setDirtyFileIds(new Set());
      setIsSubmitDialogOpen(false);
      setSubmitSuccessMessage(
        createdSubmission.status === "ready_for_review"
          ? "Final solution submitted. Tests passed and the workspace is locked for review."
          : "Final solution submitted. Tests did not pass, and the workspace is locked for interviewer review.",
      );
    } catch (requestError: unknown) {
      const message = requestError instanceof ApiError ? requestError.message : "Unable to submit final solution.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAskCopilot(questionOverride?: string) {
    const question = (questionOverride ?? copilotQuestion).trim();
    if (!token || !session || question.length === 0 || isAskingCopilot || isSubmitted) {
      return;
    }

    setIsAskingCopilot(true);
    setCopilotError(null);
    setPendingCopilotQuestion(question);
    setLastCopilotQuestion(question);
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
    } catch (requestError: unknown) {
      setCopilotError(COPILOT_UNAVAILABLE_MESSAGE);
    } finally {
      setIsAskingCopilot(false);
      setPendingCopilotQuestion(null);
    }
  }

  function handleCopilotKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    void handleAskCopilot();
  }

  return (
    <main className="flex h-screen min-h-screen flex-col overflow-hidden bg-slate-200 text-slate-950">
      <header className="shrink-0 border-b border-slate-300 bg-white/95 px-4 py-3 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              aria-label="Nexterview home"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-950 text-xs font-bold text-white shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
              href="/"
            >
              N
            </Link>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Candidate interview</p>
              <h1 className="truncate text-base font-semibold text-slate-950">
                {session?.scenario.title ?? "Preparing interview workspace"}
              </h1>
              <p className="truncate text-xs text-slate-500">
                {session ? `${session.interview.role_title} / ${session.interview.seniority} / ${session.interview.interview_type}` : user?.email}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={session?.status ?? "loading"} tone={isSubmitted ? "success" : "neutral"} />
            {session ? <StatusBadge label={sanitizeCandidateText(session.interview.allowed_ai_mode)} /> : null}
            <div className="flex h-10 items-center gap-3 rounded-lg border border-slate-300 bg-slate-100 px-3 shadow-inner">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Elapsed</span>
              <span className="font-mono text-sm font-semibold text-slate-950">{formatDuration(elapsedSeconds)}</span>
            </div>
            <span className="inline-flex h-10 items-center rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-600 shadow-sm">
              Saved {formatSavedAt(lastSavedAt)}
            </span>
            <Button
              className="h-10 px-4"
              disabled={isRunningTests || isSubmitted || !session}
              onClick={() => void handleRunTests()}
              type="button"
              variant="secondary"
            >
              {isRunningTests ? "Running checks..." : "Run tests"}
            </Button>
            <Button className="h-10 px-5" disabled={!canSubmit} onClick={() => setIsSubmitDialogOpen(true)} type="button">
              {isSubmitting ? "Submitting..." : isSubmitted ? "Submitted" : "Submit solution"}
            </Button>
          </div>
        </div>
      </header>

      <section className="min-h-0 flex-1 overflow-auto bg-[linear-gradient(135deg,rgb(241_245_249),rgb(226_232_240)_55%,rgb(219_234_254/0.7))] p-3">
        {isLoading ? (
          <WorkspaceLoadingState />
        ) : null}

        {error ? (
          <p className="mb-3 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700 shadow-sm">
            {sanitizeCandidateText(error)}
          </p>
        ) : null}

        {submitSuccessMessage ? (
          <p className="mb-3 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 shadow-sm">
            {submitSuccessMessage}
          </p>
        ) : null}

        {session ? (
          <div className="h-full min-h-[760px] min-w-[1100px]">
            <PanelGroup
              autoSaveId={`candidate-session-${session.id}-workspace`}
              className="h-full"
              direction="horizontal"
              onLayout={handleHorizontalLayout}
            >
              <Panel collapsible collapsedSize={4} defaultSize={24} id="task" maxSize={42} minSize={18} order={1} ref={taskPanelRef}>
                {minimizedPanels.has("task") ? (
                  <CollapsedPanelRestore label="Task" onRestore={() => handleRestorePanel("task")} />
                ) : (
                  <IdePanel>
                    <PanelHeader
                      eyebrow="Candidate Task"
                      isMaximized={maximizedPanel === "task"}
                      meta={session.interview.role_title}
                      onMaximize={handleMaximizePanel}
                      onMinimize={handleMinimizePanel}
                      onRestore={() => handleRestorePanel()}
                      panelId="task"
                      title="Task"
                    />
                    <CoachMark
                      arrow="top"
                      className="mx-3 mt-3 shrink-0"
                      description="Requirements and logs are candidate-visible. Hidden rubric stays private."
                      id="candidate-task-visibility"
                      title="Task context"
                      tone="dark"
                    />
                    <TaskPanel session={session} />
                  </IdePanel>
                )}
              </Panel>

              <ResizeGrip orientation="vertical" />

              <Panel collapsible collapsedSize={5} defaultSize={52} id="editor" minSize={34} order={2} ref={editorPanelRef}>
                {minimizedPanels.has("editor") ? (
                  <CollapsedPanelRestore label="Editor" onRestore={() => handleRestorePanel("editor")} />
                ) : (
                  <IdePanel>
                    <PanelHeader
                      actions={
                        <div className="hidden items-center gap-2 text-xs text-slate-400 2xl:flex">
                          {selectedFile && dirtyFileIds.has(selectedFile.id) ? <span className="text-amber-300">Unsaved</span> : null}
                          {selectedFile && savingFileIds.has(selectedFile.id) ? <span className="text-cyan-300">Saving...</span> : null}
                          {!selectedFile && isSavingCode ? <span className="text-cyan-300">Saving...</span> : null}
                          {isSubmitted ? <span>Locked</span> : null}
                        </div>
                      }
                      eyebrow="Code Workspace"
                      isMaximized={maximizedPanel === "editor"}
                      meta={selectedFile?.path ?? "starter-code"}
                      onMaximize={handleMaximizePanel}
                      onMinimize={handleMinimizePanel}
                      onRestore={() => handleRestorePanel()}
                      panelId="editor"
                      title={workspace?.project?.project_name ?? "Editor"}
                    />
                    <div className="min-h-0 flex-1">
                      <PanelGroup
                        autoSaveId={`candidate-session-${session.id}-editor-stack`}
                        direction="vertical"
                        onLayout={handleEditorPanelLayout}
                      >
                        <Panel defaultSize={70} id="code" minSize={28} order={1} ref={codePanelRef}>
                          <div className="grid h-full min-h-0 grid-cols-[220px_minmax(0,1fr)]">
                            <aside className="min-h-0 overflow-hidden border-r border-slate-700 bg-slate-900">
                              <div className="border-b border-slate-700 bg-slate-800/70 px-3 py-2">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Explorer</p>
                                <p className="mt-1 truncate text-xs text-slate-400">
                                  {workspace?.project?.description ?? "Editable starter code"}
                                </p>
                              </div>
                              <div className="h-[calc(100%-57px)] overflow-auto p-2">
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
                                    className="w-full rounded-md bg-blue-600 px-2 py-2 text-left text-xs text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-400/60"
                                    onClick={() => setSelectedFileId(null)}
                                    type="button"
                                  >
                                    starter-code.{languageForStack(session.interview.stack)}
                                  </button>
                                )}
                              </div>
                            </aside>
                            <div className="flex min-h-0 flex-col bg-slate-950">
                              <div className="flex min-h-10 items-center justify-between gap-3 border-b border-slate-800 bg-slate-900 px-2">
                                <div className="flex min-w-0 items-center self-stretch border-x border-slate-700 bg-slate-950 px-3">
                                  <span className="min-w-0 truncate text-xs font-medium text-slate-100">
                                    {selectedFile?.path ?? `starter-code.${languageForStack(session.interview.stack)}`}
                                  </span>
                                  {selectedFile && dirtyFileIds.has(selectedFile.id) ? (
                                    <span className="ml-2 h-2 w-2 shrink-0 rounded-full bg-amber-400" title="Unsaved changes" />
                                  ) : null}
                                </div>
                                <div className="flex shrink-0 items-center gap-2">
                                  <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-300">
                                    {selectedFile
                                      ? monacoLanguage(selectedFile.language)
                                      : languageForStack(session.interview.stack)}
                                  </span>
                                  {session.scenario.validation_command ? (
                                    <code
                                      className="hidden max-w-64 truncate rounded-full border border-blue-900 bg-blue-950/50 px-2.5 py-0.5 text-[10px] text-blue-200 2xl:block"
                                      title={sanitizeCandidateText(session.scenario.validation_command)}
                                    >
                                      {sanitizeCandidateText(session.scenario.validation_command)}
                                    </code>
                                  ) : null}
                                </div>
                              </div>
                              <div className="min-h-0 flex-1">
                                <MonacoEditor
                                  height="100%"
                                  language={selectedFile ? monacoLanguage(selectedFile.language) : languageForStack(session.interview.stack)}
                                  onChange={handleEditorChange}
                                  onMount={(editor) => {
                                    editorInstanceRef.current = editor;
                                    requestEditorLayout();
                                  }}
                                  options={{
                                    automaticLayout: true,
                                    fontSize: 13,
                                    minimap: { enabled: false },
                                    padding: { top: 14 },
                                    readOnly: isSubmitted || Boolean(selectedFile && !selectedFile.is_editable),
                                    scrollBeyondLastLine: false,
                                    wordWrap: "on",
                                  }}
                                  theme="vs-dark"
                                  value={selectedEditorValue}
                                />
                              </div>
                            </div>
                          </div>
                        </Panel>

                        <ResizeGrip orientation="horizontal" />

                        <Panel collapsible collapsedSize={9} defaultSize={30} id="output" minSize={18} order={2} ref={outputPanelRef}>
                          {minimizedPanels.has("output") ? (
                            <CollapsedPanelRestore
                              label={testRun ? `Output: ${testRun.status}` : "Output"}
                              onRestore={() => handleRestorePanel("output")}
                              orientation="horizontal"
                            />
                          ) : (
                            <div className="flex h-full min-h-0 flex-col border-t border-slate-800 bg-slate-950/40">
                              <PanelHeader
                                actions={
                                  testRun ? (
                                    <StatusBadge
                                      label={testRun.status === "passed" ? "Passed" : "Failed"}
                                      tone={testRun.status === "passed" ? "success" : "warning"}
                                    />
                                  ) : null
                                }
                                eyebrow="Validation cockpit"
                                isMaximized={maximizedPanel === "output"}
                                meta={
                                  isRunningTests
                                    ? "Running checks"
                                    : sanitizeCandidateText(session.scenario.validation_command || "Ready to validate")
                                }
                                onMaximize={handleMaximizePanel}
                                onMinimize={handleMinimizePanel}
                                onRestore={() => handleRestorePanel()}
                                panelId="output"
                                title="Tests & Summary"
                              />
                              <CoachMark
                                arrow="top"
                                className="mx-3 mt-3 shrink-0"
                                description="Run tests to verify your fix before submitting."
                                id="candidate-test-validation"
                                title="Validate before submission"
                                tone="dark"
                              />
                              <OutputPanel
                                isRunningTests={isRunningTests}
                                isSavingNotes={isSavingNotes}
                                isSubmitted={isSubmitted}
                                notes={notes}
                                onNotesChange={handleNotesChange}
                                onRunTests={() => void handleRunTests()}
                                submission={submission}
                                testRun={testRun}
                                testRunError={testRunError}
                                testRunStartedAt={testRunStartedAt}
                                validationCommand={session.scenario.validation_command}
                                validationInstructions={session.scenario.validation_instructions}
                              />
                            </div>
                          )}
                        </Panel>
                      </PanelGroup>
                    </div>
                  </IdePanel>
                )}
              </Panel>

              <ResizeGrip orientation="vertical" />

              <Panel collapsible collapsedSize={4} defaultSize={24} id="copilot" maxSize={38} minSize={18} order={3} ref={copilotPanelRef}>
                {minimizedPanels.has("copilot") ? (
                  <CollapsedPanelRestore label="AI" onRestore={() => handleRestorePanel("copilot")} />
                ) : (
                  <IdePanel>
                    <PanelHeader
                      actions={<StatusBadge label={sanitizeCandidateText(session.interview.allowed_ai_mode)} />}
                      eyebrow="AI Copilot"
                      isMaximized={maximizedPanel === "copilot"}
                      meta="Context-aware assistance"
                      onMaximize={handleMaximizePanel}
                      onMinimize={handleMinimizePanel}
                      onRestore={() => handleRestorePanel()}
                      panelId="copilot"
                      title="Copilot"
                    />
                    <div className="flex min-h-0 flex-1 flex-col">
                      <CoachMark
                        arrow="top"
                        className="mx-3 mt-3 shrink-0"
                        description="AI assistance is allowed. We evaluate how well candidates validate it."
                        id="candidate-ai-copilot"
                        title="AI is part of the assessment"
                        tone="dark"
                      />
                      <div className="border-b border-slate-700 bg-blue-950/25 px-4 py-3">
                        <p className="text-xs leading-5 text-blue-100">
                          Task context, current code, and latest test output are included automatically.
                        </p>
                      </div>
                      <div className="min-h-0 flex-1 overflow-auto bg-slate-900 p-4">
                        <div className="grid gap-3">
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
                              onRetry={() => {
                                if (lastCopilotQuestion) {
                                  void handleAskCopilot(lastCopilotQuestion);
                                }
                              }}
                            />
                          ) : null}
                          <div ref={copilotMessagesEndRef} />
                        </div>
                      </div>
                      <div className="border-t border-slate-700 bg-slate-800/80 p-4">
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400" htmlFor="copilot-question">
                          Ask Copilot
                        </label>
                        <textarea
                          className="mt-2 min-h-28 w-full resize-none rounded-lg border border-slate-600 bg-slate-950 px-3 py-3 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600 focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-400/40 disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={isAskingCopilot || isSubmitted}
                          id="copilot-question"
                          onChange={(event) => {
                            setCopilotQuestion(event.target.value);
                            setCopilotError(null);
                          }}
                          onKeyDown={handleCopilotKeyDown}
                          placeholder="Ask for debugging help, test ideas, code review, or tradeoff analysis."
                          value={copilotQuestion}
                        />
                        <div className="mt-3 flex items-center justify-between gap-3">
                          <p className="text-xs text-slate-500">Enter sends. Shift+Enter adds a line.</p>
                          <Button
                            className="h-9 px-4"
                            disabled={isAskingCopilot || isSubmitted || copilotQuestion.trim().length === 0}
                            onClick={() => void handleAskCopilot()}
                            type="button"
                          >
                            {isAskingCopilot ? "Sending..." : "Send"}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </IdePanel>
                )}
              </Panel>
            </PanelGroup>
          </div>
        ) : null}
      </section>

      <SubmitConfirmDialog
        isOpen={isSubmitDialogOpen}
        isSubmitting={isSubmitting}
        notes={finalExplanation}
        testRun={testRun}
        onCancel={() => {
          if (!isSubmitting) {
            setIsSubmitDialogOpen(false);
          }
        }}
        onConfirm={() => void handleSubmit()}
      />
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
