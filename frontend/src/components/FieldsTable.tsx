import { useState, useMemo } from "react";
import type { FieldEntry } from "@/types/run";
import { getFieldLabel } from "@/lib/fieldLabels";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SourceViewerDrawer } from "@/components/SourceViewerDrawer";
import { ExternalLink } from "lucide-react";

interface FieldsTableProps {
  fields: Record<string, FieldEntry>;
}

function isNotFound(val: string) {
  return val === "Not Found";
}

export function FieldsTable({ fields }: FieldsTableProps) {
  const [filter, setFilter] = useState("");
  const [hideNotFound, setHideNotFound] = useState(false);
  const [drawerField, setDrawerField] = useState<{ key: string; entry: FieldEntry } | null>(null);

  const entries = useMemo(() => {
    return Object.entries(fields)
      .map(([key, entry]) => ({ key, label: getFieldLabel(key), entry }))
      .filter((row) => {
        if (hideNotFound && isNotFound(row.entry.value)) return false;
        if (!filter) return true;
        const q = filter.toLowerCase();
        return (
          row.label.toLowerCase().includes(q) ||
          row.entry.value.toLowerCase().includes(q) ||
          row.entry.source_url.toLowerCase().includes(q)
        );
      });
  }, [fields, filter, hideNotFound]);

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <Input
          placeholder="Filter fields..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-xs"
        />
        <div className="flex items-center gap-2">
          <Switch id="hide-not-found" checked={hideNotFound} onCheckedChange={setHideNotFound} />
          <Label htmlFor="hide-not-found" className="text-sm">Show only found fields</Label>
        </div>
        <span className="text-sm text-muted-foreground ml-auto">{entries.length} fields</span>
      </div>

      {/* Table */}
      <div className="border rounded-md overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Field</TableHead>
              <TableHead>Value</TableHead>
              <TableHead className="w-[100px]">Source</TableHead>
              <TableHead className="w-[250px]">Quote</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map(({ key, label, entry }) => {
              const notFound = isNotFound(entry.value);
              return (
                <TableRow key={key}>
                  <TableCell className="font-medium text-sm">{label}</TableCell>
                  <TableCell className={`text-sm ${notFound ? "text-muted-foreground italic" : ""}`}>
                    {entry.value}
                  </TableCell>
                  <TableCell>
                    {notFound ? (
                      <span className="text-xs text-muted-foreground">—</span>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-7"
                        onClick={() => setDrawerField({ key, entry })}
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        View
                      </Button>
                    )}
                  </TableCell>
                  <TableCell className={`text-xs max-w-[250px] truncate ${notFound ? "text-muted-foreground italic" : ""}`}>
                    {isNotFound(entry.source_quote) ? "—" : entry.source_quote}
                  </TableCell>
                </TableRow>
              );
            })}
            {entries.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                  No fields match your filter.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Source viewer drawer */}
      {drawerField && (
        <SourceViewerDrawer
          open={!!drawerField}
          onOpenChange={(open) => !open && setDrawerField(null)}
          url={drawerField.entry.source_url}
          quote={drawerField.entry.source_quote}
          fieldLabel={getFieldLabel(drawerField.key)}
        />
      )}
    </div>
  );
}
