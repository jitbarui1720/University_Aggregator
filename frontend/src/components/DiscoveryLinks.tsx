import type { Discovery } from "@/types/run";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";

function LinkRow({ label, url }: { label: string; url: string }) {
  return (
    <div className="flex items-center justify-between text-sm py-1">
      <span className="text-muted-foreground">{label}</span>
      <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-primary hover:underline truncate max-w-[60%]">
        <ExternalLink className="h-3 w-3 shrink-0" />
        <span className="truncate">{new URL(url).hostname}</span>
      </a>
    </div>
  );
}

export function DiscoveryLinks({ discovery }: { discovery: Discovery }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Discovery Links</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <LinkRow label="Program" url={discovery.program_url} />
        <LinkRow label="Tuition" url={discovery.tuition_url} />
        <LinkRow label="Faculty" url={discovery.faculty_url} />
        <LinkRow label="Admissions" url={discovery.admissions_url} />
        {discovery.context_urls.length > 0 && (
          <div className="pt-2 border-t mt-2">
            <p className="text-sm text-muted-foreground mb-1">Context URLs ({discovery.context_urls.length})</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {discovery.context_urls.map((url, i) => (
                <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="block text-xs text-primary hover:underline truncate">
                  {url}
                </a>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
