import type { AIMode, Difficulty, InterviewType, Seniority } from "@/lib/types";

export const seniorityOptions: Array<{ label: string; value: Seniority }> = [
  { label: "Junior", value: "JUNIOR" },
  { label: "Mid-level", value: "MID" },
  { label: "Senior", value: "SENIOR" },
  { label: "Staff", value: "STAFF" },
];

export const interviewTypeOptions: Array<{ label: string; value: InterviewType }> = [
  { label: "Full-stack feature", value: "FULL_STACK_FEATURE" },
  { label: "Backend debugging", value: "BACKEND_DEBUGGING" },
  { label: "API design", value: "API_DESIGN" },
  { label: "Frontend bug fix", value: "FRONTEND_BUG_FIX" },
  { label: "System design", value: "SYSTEM_DESIGN" },
  { label: "AI engineering", value: "AI_ENGINEERING" },
  { label: "Refactoring", value: "REFACTORING" },
  { label: "Security review", value: "SECURITY_REVIEW" },
];

export const difficultyOptions: Array<{ label: string; value: Difficulty }> = [
  { label: "Easy", value: "EASY" },
  { label: "Medium", value: "MEDIUM" },
  { label: "Hard", value: "HARD" },
];

export const aiModeOptions: Array<{ label: string; value: AIMode }> = [
  { label: "Hint mode", value: "HINT" },
  { label: "Pair programmer", value: "PAIR_PROGRAMMER" },
  { label: "Senior engineer", value: "SENIOR_ENGINEER" },
  { label: "Debugging assistant", value: "DEBUGGING_ASSISTANT" },
];

export function optionLabel<T extends string>(options: Array<{ label: string; value: T }>, value: T): string {
  return options.find((option) => option.value === value)?.label ?? value;
}
