import { useEffect, useMemo, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ExternalLink, Copy, Check } from "lucide-react";
import { appendTextFragment } from "@/lib/textFragment";

interface SourceViewerDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  url: string;
  quote: string;
  fieldLabel: string;
}

export function SourceViewerDrawer({ open, onOpenChange, url, quote, fieldLabel }: SourceViewerDrawerProps) {
  const [iframeFailed, setIframeFailed] = useState(false);
  const [copied, setCopied] = useState(false);

  const urlWithHighlight = useMemo(() => appendTextFragment(url, quote), [url, quote]);

  useEffect(() => {
    if (open) setIframeFailed(false);
  }, [open, urlWithHighlight]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(quote);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Source: {fieldLabel}</SheetTitle>
          <SheetDescription className="break-all text-xs">{url}</SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          <div className="border rounded-md overflow-hidden" style={{ height: 350 }}>
            {!iframeFailed ? (
              <iframe
                key={urlWithHighlight}
                src={urlWithHighlight}
                title="Source viewer"
                className="w-full h-full"
                // allow-scripts: pages must run JS for DOM to contain the quoted text; otherwise #:~:text has nothing to match.
                // allow-same-origin: lets same-origin frames behave normally; cross-origin sources still cannot access the parent.
                sandbox="allow-scripts allow-same-origin"
                referrerPolicy="strict-origin-when-cross-origin"
                onError={() => setIframeFailed(true)}
                onLoad={(e) => {
                  try {
                    // Access check - will throw if blocked
                    const frame = e.currentTarget;
                    if (!frame.contentDocument && !frame.contentWindow) {
                      setIframeFailed(true);
                    }
                  } catch {
                    setIframeFailed(true);
                  }
                }}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
                <p className="text-sm">This page cannot be embedded (blocked by the source site).</p>
                <Button variant="outline" size="sm" asChild>
                  <a href={urlWithHighlight} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4 mr-1" />
                    Open in new tab
                  </a>
                </Button>
              </div>
            )}
          </div>

          {/* Evidence quote */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium">Evidence</h4>
              <Button variant="ghost" size="sm" onClick={handleCopy}>
                {copied ? <Check className="h-4 w-4 mr-1" /> : <Copy className="h-4 w-4 mr-1" />}
                {copied ? "Copied" : "Copy Quote"}
              </Button>
            </div>
            <div className="rounded-md border p-3 text-sm">{quote}</div>
          </div>

          <Button variant="outline" className="w-full" asChild>
            <a href={urlWithHighlight} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-1" />
              Open in new tab
            </a>
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
