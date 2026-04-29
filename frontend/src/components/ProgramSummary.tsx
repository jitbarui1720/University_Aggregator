import type { RunResult } from "@/types/run";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ProgramSummary({ result }: { result: RunResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Program Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Program</span>
          <span className="font-medium text-right max-w-[60%]">{result.discovery.program_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Type</span>
          <span>{result.discovery.program_type || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Institution</span>
          <span>{result.college_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Valid Certificate</span>
          <span>{result.discovery.is_valid_certificate || "—"}</span>
        </div>
      </CardContent>
    </Card>
  );
}
