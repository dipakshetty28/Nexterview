'use client';

import { useState } from 'react';

type Scenario = {
  id: number;
  interview_id: number;
  title: string;
  business_context: string;
  technical_requirements: string;
  starter_code: string;
  expected_behavior: string;
  logs_or_bug_report: string;
  hidden_evaluation_points: string;
  candidate_instructions: string;
  interviewer_rubric: string;
};

export default function InterviewDetailPage({ params }: { params: { id: string } }) {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateScenario = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/interviews/${params.id}/generate-scenario`, { method: 'POST' });
      if (!response.ok) {
        throw new Error('Failed to generate scenario');
      }
      const data = await response.json();
      setScenario(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Interview #{params.id}</h1>
      <button
        className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
        onClick={generateScenario}
        disabled={loading}
      >
        {loading ? 'Generating...' : 'Generate Scenario with AI'}
      </button>
      {error && <p className="text-red-600">{error}</p>}
      {scenario && (
        <section className="space-y-2 border rounded p-4">
          <h2 className="text-xl font-semibold">{scenario.title}</h2>
          <p><strong>Business Context:</strong> {scenario.business_context}</p>
          <p><strong>Technical Requirements:</strong> {scenario.technical_requirements}</p>
          <pre className="bg-gray-100 p-2 overflow-auto"><code>{scenario.starter_code}</code></pre>
          <p><strong>Expected Behavior:</strong> {scenario.expected_behavior}</p>
          <p><strong>Logs / Bug Report:</strong> {scenario.logs_or_bug_report}</p>
          <p><strong>Hidden Evaluation Points:</strong> {scenario.hidden_evaluation_points}</p>
          <p><strong>Candidate Instructions:</strong> {scenario.candidate_instructions}</p>
          <p><strong>Interviewer Rubric:</strong> {scenario.interviewer_rubric}</p>
        </section>
      )}
    </main>
  );
}
