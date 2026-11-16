import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export interface TabItem {
  id: string;
  label: ReactNode;
  content: ReactNode;
  /** Printed even when not the active tab (report and sources). */
  printable?: boolean;
}

interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  /** Accessible name of the tab list. */
  label: string;
  idPrefix: string;
}

/** WAI-ARIA tabs with roving focus (arrow keys, Home/End). */
export function Tabs({ items, activeId, onChange, label, idPrefix }: TabsProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const focusTab = (index: number) => {
    const item = items[(index + items.length) % items.length];
    if (!item) return;
    onChange(item.id);
    listRef.current?.querySelector<HTMLButtonElement>(`#${idPrefix}-tab-${item.id}`)?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = items.findIndex((item) => item.id === activeId);
    const keys: Record<string, number> = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: items.length - 1,
    };
    const target = keys[event.key];
    if (target === undefined) return;
    event.preventDefault();
    focusTab(target);
  };

  return (
    <div>
      <div
        ref={listRef}
        role="tablist"
        aria-label={label}
        className="-mx-1 flex gap-1 overflow-x-auto border-b border-line px-1 print:hidden"
      >
        {items.map((item) => {
          const selected = item.id === activeId;
          return (
            <button
              key={item.id}
              id={`${idPrefix}-tab-${item.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`${idPrefix}-panel-${item.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.id)}
              onKeyDown={onKeyDown}
              className={cn(
                "-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
                "focus-visible:outline-offset-[-2px]",
                selected
                  ? "border-accent-solid text-fg"
                  : "border-transparent text-fg-muted hover:border-line-strong hover:text-fg",
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {items.map((item) => {
        const selected = item.id === activeId;
        return (
          <div
            key={item.id}
            id={`${idPrefix}-panel-${item.id}`}
            role="tabpanel"
            aria-labelledby={`${idPrefix}-tab-${item.id}`}
            tabIndex={0}
            className={cn(
              "pt-6 focus-visible:outline-offset-4",
              selected ? "block" : "hidden",
              item.printable ? "print:block" : "print:hidden",
            )}
          >
            {item.content}
          </div>
        );
      })}
    </div>
  );
}
