import { useState, useEffect, useCallback } from "react";
import type { Run } from "@/types/run";
import { createRun, getRun } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { RunStatusPanel } from "@/components/RunStatusPanel";
import { ProgramSummary } from "@/components/ProgramSummary";
import { DiscoveryLinks } from "@/components/DiscoveryLinks";
import { FieldsTable } from "@/components/FieldsTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Button } from "@/components/ui/button";

export default function Index() {
  const [run, setRun] = useState<Run | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isTerminal = run && (run.status === "completed" || run.status === "failed" || run.status === "invalid_program");

  // Polling
  useEffect(() => {
    if (!run || isTerminal) return;
    const interval = setInterval(async () => {
      try {
        const updated = await getRun(run.run_id);
        setRun(updated);
      } catch (e) {
        console.error("Polling error:", e);
      }
    },5000);
    return () => clearInterval(interval);
  }, [run, isTerminal]);

  const handleSearch = useCallback(async (collegeName: string) => {
    setIsSubmitting(true);
    try {
      const newRun = await createRun(collegeName);
      setRun(newRun);
    } catch (e) {
      console.error("Error creating run:", e);
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const isCompleted = run?.status === "completed" && run.result;
  const isFailed = run?.status === "failed" || run?.status === "invalid_program";

  const handleDownloadJson = useCallback(() => {
    if (!run?.result) return;

    const jsonData = JSON.stringify(run.result, null, 2);
    const blob = new Blob([jsonData], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const safeCollegeName = (run.result.college_name || run.college_name || "college")
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, "")
      .trim()
      .replace(/\s+/g, "_");
    const filename = `${safeCollegeName || "college"}.json`;

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [run]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4">
        <h1 className="text-xl font-semibold">University Aggregator</h1>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 space-y-6">
        {/* Search */}
        <div className="flex justify-center">
          <SearchBar onSearch={handleSearch} isLoading={isSubmitting || (!!run && !isTerminal)} />
        </div>

        {/* Empty state */}
        {!run && <EmptyState />}

        {/* Status */}
        {run && <RunStatusPanel run={run} />}

        {/* Error/Invalid */}
        {isFailed && run && <ErrorState run={run} />}

        {/* Results */}
        {isCompleted && run.result && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ProgramSummary result={run.result} />
              <DiscoveryLinks discovery={run.result.discovery} />
            </div>

            

            <div>
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">Extracted Fields</h2>
                <Button type="button" variant="outline" size="sm" onClick={handleDownloadJson}>
                  Download
                </Button>
              </div>
              <FieldsTable fields={run.result.fields} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
