import { useParams, useSearchParams } from "react-router-dom";

export default function ImportResultsSimple() {
  const { jobId } = useParams<{ jobId: string }>();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get('mode') as 'draft' | 'supplier' || 'draft';

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-4">Import Results Test Page</h1>
        <div className="bg-white p-6 rounded-lg shadow">
          <p><strong>Job ID:</strong> {jobId || 'Missing'}</p>
          <p><strong>Mode:</strong> {mode}</p>
          <p><strong>URL:</strong> {window.location.href}</p>

          <div className="mt-6">
            <h2 className="text-xl font-semibold mb-2">
              {mode === 'draft' ? 'Draft LC Risk Analysis' : 'Supplier Document Compliance'}
            </h2>
            <p>
              {mode === 'draft'
                ? 'This would show LC risk analysis results'
                : 'This would show document compliance results'
              }
            </p>
          </div>

          <div className="mt-6">
            <h3 className="font-semibold">Test URLs:</h3>
            <ul className="mt-2 space-y-1 text-sm">
              <li>
                <a href="/import/results/test-123?mode=draft" className="text-blue-600 hover:underline">
                  Draft mode: /import/results/test-123?mode=draft
                </a>
              </li>
              <li>
                <a href="/import/results/test-456?mode=supplier" className="text-blue-600 hover:underline">
                  Supplier mode: /import/results/test-456?mode=supplier
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}