"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, createInterview } from "@/lib/api";
import { aiModeOptions, difficultyOptions, interviewTypeOptions, seniorityOptions } from "@/lib/interview-options";
import type { AIMode, Difficulty, InterviewType, Seniority } from "@/lib/types";

function CreateInterviewContent() {
  const router = useRouter();
  const { token, user } = useAuth();
  const organizations = user?.organizations ?? [];
  const [organizationId, setOrganizationId] = useState(organizations[0]?.organization.id ?? "");
  const [title, setTitle] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [seniority, setSeniority] = useState<Seniority>("SENIOR");
  const [stack, setStack] = useState("Python, FastAPI, PostgreSQL");
  const [interviewType, setInterviewType] = useState<InterviewType>("BACKEND_DEBUGGING");
  const [difficulty, setDifficulty] = useState<Difficulty>("MEDIUM");
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [aiMode, setAiMode] = useState<AIMode>("PAIR_PROGRAMMER");
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [businessContext, setBusinessContext] = useState("");
  const [candidateInstructions, setCandidateInstructions] = useState("");
  const [technicalRequirements, setTechnicalRequirements] = useState("");
  const [evaluationRubric, setEvaluationRubric] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const canManageInterviews = user?.role === "ADMIN" || user?.role === "INTERVIEWER";

  const stackItems = useMemo(() => stack.split(",").map((item) => item.trim()).filter(Boolean), [stack]);

  useEffect(() => {
    if (!organizationId && organizations.length > 0) {
      setOrganizationId(organizations[0].organization.id);
    }
  }, [organizationId, organizations]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const interview = await createInterview(token, {
        organization_id: organizationId || undefined,
        title,
        role_title: roleTitle,
        seniority,
        stack: stackItems,
        interview_type: interviewType,
        difficulty,
        duration_minutes: durationMinutes,
        ai_mode: aiMode,
        scenario: {
          title: scenarioTitle,
          business_context: businessContext,
          candidate_instructions: candidateInstructions,
          technical_requirements: technicalRequirements,
          evaluation_rubric: evaluationRubric,
        },
      });
      router.push(`/interviews/${interview.id}`);
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to create interview.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!canManageInterviews) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-md border border-slate-800 bg-slate-900/60 p-6">
          <h1 className="text-2xl font-semibold">Interview management is unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-slate-400">Your account role does not include interviewer access.</p>
          <Link className="mt-6 inline-flex text-sm font-medium text-cyan-300 hover:text-cyan-200" href="/dashboard">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div>
            <Link className="text-sm text-slate-400 hover:text-slate-200" href="/dashboard">
              Dashboard
            </Link>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">Create interview</h1>
          </div>
        </div>
      </header>
      <form className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[1fr_360px]" onSubmit={handleSubmit}>
        <section className="grid gap-6">
          <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-xl font-semibold">Interview setup</h2>
            <div className="mt-6 grid gap-5 md:grid-cols-2">
              {organizations.length > 1 ? (
                <Select id="organization" label="Organization" value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} required>
                  {organizations.map((membership) => (
                    <option key={membership.organization.id} value={membership.organization.id}>
                      {membership.organization.name}
                    </option>
                  ))}
                </Select>
              ) : null}
              <Input id="title" label="Title" value={title} onChange={(event) => setTitle(event.target.value)} required />
              <Input id="roleTitle" label="Role title" value={roleTitle} onChange={(event) => setRoleTitle(event.target.value)} required />
              <Select id="seniority" label="Seniority" value={seniority} onChange={(event) => setSeniority(event.target.value as Seniority)}>
                {seniorityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <Select id="interviewType" label="Interview type" value={interviewType} onChange={(event) => setInterviewType(event.target.value as InterviewType)}>
                {interviewTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <Select id="difficulty" label="Difficulty" value={difficulty} onChange={(event) => setDifficulty(event.target.value as Difficulty)}>
                {difficultyOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <Input
                id="duration"
                label="Duration minutes"
                type="number"
                min={15}
                max={240}
                value={durationMinutes}
                onChange={(event) => setDurationMinutes(Number(event.target.value))}
                required
              />
              <Select id="aiMode" label="AI mode" value={aiMode} onChange={(event) => setAiMode(event.target.value as AIMode)}>
                {aiModeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <Input className="md:col-span-2" id="stack" label="Stack" value={stack} onChange={(event) => setStack(event.target.value)} required />
            </div>
          </div>
          <div className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-xl font-semibold">Manual scenario</h2>
            <div className="mt-6 grid gap-5">
              <Input id="scenarioTitle" label="Scenario title" value={scenarioTitle} onChange={(event) => setScenarioTitle(event.target.value)} required />
              <Textarea id="businessContext" label="Business context" value={businessContext} onChange={(event) => setBusinessContext(event.target.value)} required />
              <Textarea
                id="candidateInstructions"
                label="Candidate instructions"
                value={candidateInstructions}
                onChange={(event) => setCandidateInstructions(event.target.value)}
                required
              />
              <Textarea
                id="technicalRequirements"
                label="Technical requirements"
                value={technicalRequirements}
                onChange={(event) => setTechnicalRequirements(event.target.value)}
                required
              />
              <Textarea id="evaluationRubric" label="Evaluation rubric" value={evaluationRubric} onChange={(event) => setEvaluationRubric(event.target.value)} required />
            </div>
          </div>
        </section>
        <aside className="h-fit rounded-md border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-lg font-semibold">Review</h2>
          <div className="mt-5 grid gap-3 text-sm text-slate-400">
            <div className="flex justify-between gap-4">
              <span>Stack items</span>
              <span className="text-slate-200">{stackItems.length}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>Duration</span>
              <span className="text-slate-200">{durationMinutes} min</span>
            </div>
            <div className="flex justify-between gap-4">
              <span>Status</span>
              <span className="text-slate-200">Draft</span>
            </div>
          </div>
          {error ? <p className="mt-5 rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}
          <Button className="mt-6 w-full" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create interview"}
          </Button>
        </aside>
      </form>
    </main>
  );
}

export default function CreateInterviewPage() {
  return (
    <ProtectedRoute>
      <CreateInterviewContent />
    </ProtectedRoute>
  );
}
