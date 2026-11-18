import { Activity, Award, BookOpen, CalendarCheck, Check, ChevronsUpDown, CircleCheckBig, GraduationCap, House, ListChecks, Megaphone, Moon, Settings, Sun } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarMenu,
  SidebarMenuBadge, SidebarMenuButton, SidebarMenuItem, SidebarRail,
} from '@/components/ui/sidebar'
import { initials } from '@/format'
import { PAGE_TITLES, type Page } from '@/lib/router'

const GROUPS: { label: string; items: { key: Page; icon: typeof House }[] }[] = [
  { label: 'Study', items: [{ key: 'home', icon: House }, { key: 'assignments', icon: ListChecks }, { key: 'attendance', icon: CalendarCheck }, { key: 'exams', icon: GraduationCap }, { key: 'results', icon: Award }] },
  { label: 'Material', items: [{ key: 'lectures', icon: BookOpen }, { key: 'announcements', icon: Megaphone }] },
  { label: 'App', items: [{ key: 'activity', icon: Activity }, { key: 'settings', icon: Settings }] },
]

export const PALETTES = [{ key: 'royal', label: 'Royal' }, { key: 'ink', label: 'Ink' }, { key: 'forest', label: 'Forest' }, { key: 'ember', label: 'Ember' }] as const

export function AppSidebar({ name, semester, badges, dark, onToggleTheme, page, onNavigate, palette, onPalette }: {
  name?: string; semester?: string; badges: Partial<Record<Page, number>>; dark: boolean; onToggleTheme: () => void
  page: Page; onNavigate: (p: Page) => void; palette: string; onPalette: (p: string) => void
}) {
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

      <SidebarContent>
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
              <DropdownMenuContent side="top" align="start" className="min-w-56">
                <DropdownMenuLabel className="text-muted-foreground text-xs font-normal">{name ?? 'Student'}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={onToggleTheme}>
                  {dark ? <Sun /> : <Moon />}{dark ? 'Light theme' : 'Dark theme'}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="text-muted-foreground text-xs font-normal">Palette</DropdownMenuLabel>
                {PALETTES.map(p => (
                  <DropdownMenuItem key={p.key} onSelect={() => onPalette(p.key)}>{p.label}{palette === p.key && <Check className="ml-auto" />}</DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => onNavigate('settings')}><Settings />Settings</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
