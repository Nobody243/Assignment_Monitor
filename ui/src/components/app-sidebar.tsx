import { Award, BookOpen, Check, CalendarCheck, ChevronsUpDown, CircleCheckBig, GraduationCap, House, ListChecks, Moon, Settings, Sun } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarMenu,
  SidebarMenuBadge, SidebarMenuButton, SidebarMenuItem, SidebarRail,
} from '@/components/ui/sidebar'
import { initials } from '@/format'

const NAV = [
  { key: 'home', label: 'Home', icon: House },
  { key: 'assignments', label: 'Assignments', icon: ListChecks },
  { key: 'attendance', label: 'Attendance', icon: CalendarCheck },
  { key: 'exams', label: 'Exams', icon: GraduationCap },
  { key: 'lectures', label: 'Lectures', icon: BookOpen },
  { key: 'results', label: 'Results', icon: Award },
]

export const PALETTES = [{ key: 'royal', label: 'Royal' }, { key: 'ink', label: 'Ink' }, { key: 'forest', label: 'Forest' }] as const

export function AppSidebar({ name, semester, dueSoon, dark, onToggleTheme, page, onNavigate, palette, onPalette }: {
  name?: string; semester?: string; dueSoon: number; dark: boolean; onToggleTheme: () => void
  page: 'home' | 'assignments'; onNavigate: (p: 'home' | 'assignments') => void
  palette: string; onPalette: (p: string) => void
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
        <SidebarGroup>
          <SidebarGroupLabel>Study</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map(n => {
                const live = n.key === 'home' || n.key === 'assignments'
                return (
                  <SidebarMenuItem key={n.key}>
                    <SidebarMenuButton tooltip={n.label} isActive={n.key === page} disabled={!live} className={live ? '' : 'opacity-50'}
                      onClick={() => live && onNavigate(n.key as 'home' | 'assignments')}>
                      <n.icon />
                      <span>{n.label}</span>
                    </SidebarMenuButton>
                    {live
                      ? n.key === 'assignments' && dueSoon > 0 && <SidebarMenuBadge>{dueSoon}</SidebarMenuBadge>
                      : <SidebarMenuBadge><Badge variant="outline" className="h-4 px-1.5 text-[10px] font-normal">Soon</Badge></SidebarMenuBadge>}
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
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
                <DropdownMenuItem disabled><Settings />Settings (soon)</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
