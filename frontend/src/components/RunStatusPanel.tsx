import type { Run, RunStatus } from "@/types/run";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

const STATUS_CONFIG: Record<RunStatus, { label: string; className: string }> = {
  running: { label: "Running", className: "bg-accent text-accent-foreground" },
  completed: { label: "Completed", className: "bg-primary text-primary-foreground" },
  failed: { label: "Failed", className: "bg-destructive text-destructive-foreground" },
  invalid_program: { label: "Invalid Program", className: "bg-destructive text-destructive-foreground" },
};

const STEPS = ["Discover", "Validate", "Extract"] as const;

function inferStep(run: Run): number {
  if (run.status === "completed") return 3;
  if (run.status === "failed" || run.status === "invalid_program") return -1;
  if (run.result?.discovery) return 2;
  return 1;
}

function formatDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString();
}

export function RunStatusPanel({ run }: { run: Run }) {
  const config = STATUS_CONFIG[run.status];
  const currentStep = inferStep(run);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{run.college_name}</CardTitle>
          <Badge className={config.className}>{config.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stepper */}
        <div className="flex items-center gap-2">
          {STEPS.map((step, i) => {
            const stepNum = i + 1;
            const isDone = currentStep >= stepNum;
            const isActive = currentStep === stepNum && run.status === "running";
            return (
              <div key={step} className="flex items-center gap-1">
                {isDone ? (
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : currentStep === -1 ? (
                  <XCircle className="h-5 w-5 text-destructive" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground" />
                )}
                <span className={`text-sm ${isDone ? "font-medium" : "text-muted-foreground"}`}>{step}</span>
                {i < STEPS.length - 1 && <div className="mx-2 h-px w-8 bg-border" />}
              </div>
            );
          })}
        </div>

        {/* Timestamps */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Created</p>
            <p>{formatDate(run.created_at)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Updated</p>
            <p>{formatDate(run.updated_at)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Finished</p>
            <p>{formatDate(run.finished_at)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
