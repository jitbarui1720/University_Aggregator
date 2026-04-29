import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Copy, Check } from "lucide-react";

interface CsvPathsProps {
  csvPaths: { discovery_csv: string; full_csv: string };
}

function CopyableRow({ label, path }: { label: string; path: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <div className="min-w-0">
        <span className="text-muted-foreground">{label}: </span>
        <code className="text-xs break-all">{path}</code>
      </div>
      <Button variant="ghost" size="sm" onClick={handleCopy} className="shrink-0">
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      </Button>
    </div>
  );
}

export function CsvPaths({ csvPaths }: CsvPathsProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">CSV Outputs</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <CopyableRow label="Discovery" path={csvPaths.discovery_csv} />
        <CopyableRow label="Full" path={csvPaths.full_csv} />
      </CardContent>
    </Card>
  );
}
