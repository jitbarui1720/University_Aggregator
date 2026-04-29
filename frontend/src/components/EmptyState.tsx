import { Search } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
      <Search className="h-12 w-12" />
      <p className="text-lg font-medium">Search for a college to begin</p>
      <p className="text-sm">Enter a college name above and run the aggregation pipeline.</p>
    </div>
  );
}
