import { ArrowRight, Moon, RefreshCw } from 'lucide-react'
import type { Assignment } from '@/api'
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from '@/components/ui/command'
import { dueParts } from '@/format'

export function CommandMenu({ open, onOpenChange, assignments, dark, onPick, onSync, onToggleTheme }: {
  open: boolean; onOpenChange: (o: boolean) => void; assignments: Assignment[]; dark: boolean
  onPick: (id: string) => void; onSync: () => void; onToggleTheme: () => void
}) {
  const run = (fn: () => void) => () => { onOpenChange(false); fn() }
  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Search" description="Search assignments or run a command">
      <CommandInput placeholder="Search assignments or type a command" />
      <CommandList>
        <CommandEmpty>Nothing matches.</CommandEmpty>
        <CommandGroup heading="Commands">
          <CommandItem onSelect={run(onSync)}><RefreshCw />Check the portal now</CommandItem>
          <CommandItem onSelect={run(onToggleTheme)}><Moon />{dark ? 'Switch to the light theme' : 'Switch to the dark theme'}</CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Assignments">
          {assignments.map(a => (
            <CommandItem key={a.id} value={`${a.title} ${a.course}`} onSelect={run(() => onPick(a.id))}>
              <ArrowRight />
              <span className="truncate">{a.title}</span>
              <span className="text-muted-foreground ml-auto truncate pl-3 text-xs">{a.course} · {dueParts(a.due_at).day}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
