import { useRef } from 'react'
import { Award, BookOpen, CalendarCheck, CalendarDays, ChevronsUpDown, CircleCheckBig, GraduationCap, House, ListChecks, Megaphone, Moon, Palette, PanelLeft, Settings, Sun } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator,
  DropdownMenuShortcut, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarMenu,
  SidebarMenuBadge, SidebarMenuButton, SidebarMenuItem, SidebarRail, useSidebar,
} from '@/components/ui/sidebar'
import { initials } from '@/format'
import { PAGE_TITLES, type Page } from '@/lib/router'
import { SlideMarker } from '@/lib/slide'

const GROUPS: { label: string; items: { key: Page; icon: typeof House }[] }[] = [
  { label: 'Study', items: [{ key: 'home', icon: House }, { key: 'assignments', icon: ListChecks }, { key: 'attendance', icon: CalendarCheck }, { key: 'exams', icon: GraduationCap }, { key: 'timetable', icon: CalendarDays }, { key: 'results', icon: Award }] },
  { label: 'Material', items: [{ key: 'lectures', icon: BookOpen }, { key: 'announcements', icon: Megaphone }] },
  { label: 'App', items: [{ key: 'settings', icon: Settings }] },
]

/** The pages in the order the sidebar lists them (a page enters from the side it lies on). */
export const NAV_ORDER: readonly string[] = GROUPS.flatMap(g => g.items.map(i => i.key))

const SWATCH: Record<string, string> = { royal: 'oklch(0.84 0.13 205)', ink: 'oklch(0.2 0.012 80)', forest: 'oklch(0.9 0.2 122)', ember: 'oklch(0.7 0.19 38)' }

export const PALETTES = [{ key: 'royal', label: 'Royal' }, { key: 'ink', label: 'Ink' }, { key: 'forest', label: 'Forest' }, { key: 'ember', label: 'Ember' }] as const

export function AppSidebar({ name, semester, badges, dark, onToggleTheme, page, onNavigate, palette, onPalette }: {
  name?: string; semester?: string; badges: Partial<Record<Page, number>>; dark: boolean; onToggleTheme: () => void
  page: Page; onNavigate: (p: Page) => void; palette: string; onPalette: (p: string) => void
}) {
  const navRef = useRef<HTMLDivElement>(null)
  const { toggleSidebar } = useSidebar()
  // Up and Down (and Home and End) walk the list the way a menu does; Enter or Space opens the page (a button already does)
  const walk = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
    const items = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>("[data-sidebar='menu-button']"))
    if (!items.length) return
    const at = items.indexOf(document.activeElement as HTMLButtonElement)
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? items.length - 1 : e.key === 'ArrowDown' ? (at + 1) % items.length : (at - 1 + items.length) % items.length
    e.preventDefault()
    items[next].focus()
  }
  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="hover:bg-transparent active:bg-transparent">
              <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                <CircleCheckBig className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">Assignment Monitor</span>
                <span className="text-muted-foreground truncate text-xs">Bahria University</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent ref={navRef} role="navigation" aria-label="Main" className="slide-host relative" onKeyDown={walk}>
        <SlideMarker host={navRef} selector="[data-sidebar='menu-button'][data-active='true']" watch={page} className="slide-pill bg-sidebar-accent rounded-md" />
        {GROUPS.map(g => (
          <SidebarGroup key={g.label}>
            <SidebarGroupLabel>{g.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {g.items.map(n => (
                  <SidebarMenuItem key={n.key}>
                    <SidebarMenuButton tooltip={PAGE_TITLES[n.key]} isActive={n.key === page} onClick={() => onNavigate(n.key)}>
                      <n.icon />
                      <span>{PAGE_TITLES[n.key]}</span>
                    </SidebarMenuButton>
                    {(badges[n.key] ?? 0) > 0 && <SidebarMenuBadge>{badges[n.key]}</SidebarMenuBadge>}
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent">
                  <Avatar className="size-8 rounded-lg">
                    <AvatarFallback className="rounded-lg text-xs">{initials(name)}</AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-medium">{name ?? 'Student'}</span>
                    <span className="text-muted-foreground truncate text-xs">{semester ?? ''}</span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="min-w-60">
                <DropdownMenuLabel className="text-muted-foreground text-xs font-normal">{name ?? 'Student'}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>{dark ? <Moon /> : <Sun />}Theme</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent className="min-w-40">
                    <DropdownMenuRadioGroup value={dark ? 'dark' : 'light'} onValueChange={v => { if ((v === 'dark') !== dark) onToggleTheme() }}>
                      <DropdownMenuRadioItem value="light"><Sun />Light</DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="dark"><Moon />Dark</DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger><Palette />Palette</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent className="min-w-44">
                    <DropdownMenuRadioGroup value={palette} onValueChange={onPalette}>
                      {PALETTES.map(p => (
                        <DropdownMenuRadioItem key={p.key} value={p.key}>
                          <span aria-hidden="true" className="size-3.5 rounded-full ring-1 ring-foreground/15" style={{ background: SWATCH[p.key] }} />{p.label}
                        </DropdownMenuRadioItem>
                      ))}
                    </DropdownMenuRadioGroup>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={toggleSidebar}><PanelLeft />Collapse sidebar<DropdownMenuShortcut>Ctrl B</DropdownMenuShortcut></DropdownMenuItem>
                <DropdownMenuItem onSelect={() => onNavigate('settings')}><Settings />Settings and profile<DropdownMenuShortcut>Ctrl 9</DropdownMenuShortcut></DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
