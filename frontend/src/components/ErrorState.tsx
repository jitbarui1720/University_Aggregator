import type { Run } from "@/types/run";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

export function ErrorState({ run }: { run: Run }) {
  const isInvalid = run.status === "invalid_program";
  return (
    <Card className="border-destructive">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-5 w-5" />
          {isInvalid ? "Invalid Program" : "Run Failed"}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm">
        {isInvalid && run.result?.validation ? (
          <p>{run.result.validation.reason}</p>
        ) : run.error ? (
          <p>{run.error.message}</p>
        ) : (
          <p>An unexpected error occurred. Please try again.</p>
        )}
      </CardContent>
    </Card>
  );
}
