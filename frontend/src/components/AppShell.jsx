import { Link, NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Sun, Moon, LogOut, Menu, X } from 'lucide-react';
import { useAuth } from '../lib/auth';

const NAV = [
  { to: '/projects', label: 'Projects' },
  { to: '/history', label: 'History' },
];

function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'light';
    const stored = localStorage.getItem('rs-theme');
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') root.classList.add('dark');
    else root.classList.remove('dark');
    localStorage.setItem('rs-theme', theme);
  }, [theme]);
  return [theme, setTheme];
}

export default function AppShell() {
  const { user, signOut } = useAuth();
  const [theme, setTheme] = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const isAnalysisPage = /^\/analyses\/[^/]+$/.test(location.pathname);

  const handleSignOut = async () => {
    try {
      await signOut?.();
    } catch {
      /* signOut optional / may fail silently */
    }
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-paper-50 text-ink-900">
      <header className="sticky top-0 z-30 bg-paper-50/85 backdrop-blur-sm border-b border-rule-200 shadow-hairline">
        <div className="mx-auto max-w-[1240px] px-6 lg:px-10 h-14 flex items-center gap-6">
          <Link to="/projects" className="flex items-center gap-2 shrink-0 focus-ring rounded">
            <span className="font-serif text-[20px] tracking-[-0.01em] text-ink-900">
              ReviewScope<span className="text-accent-600">.</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `py-1 font-sans text-[12px] uppercase tracking-[0.14em] border-b transition-colors ${
                    isActive
                      ? 'text-ink-900 border-accent-600'
                      : 'text-ink-500 border-transparent hover:text-ink-900'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            {user?.email && (
              <span className="hidden lg:inline font-mono text-[12px] text-ink-500 max-w-[220px] truncate">
                {user.email}
              </span>
            )}
            <button
              type="button"
              aria-label="Toggle theme"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="btn-ghost !h-9 !w-9 !p-0"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button type="button" onClick={handleSignOut} className="btn-secondary !h-9 hidden sm:inline-flex">
              <LogOut size={15} /> Sign out
            </button>
            <button
              type="button"
              aria-label="Toggle menu"
              className="md:hidden btn-ghost !h-9 !w-9 !p-0"
              onClick={() => setMobileOpen((v) => !v)}
            >
              {mobileOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden px-6 pb-3 flex flex-col gap-1 border-t border-rule-200 bg-paper-50">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `h-11 px-1 flex items-center font-sans text-[13px] uppercase tracking-[0.1em] ${
                    isActive ? 'text-ink-900' : 'text-ink-600'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
            <button type="button" onClick={handleSignOut} className="btn-secondary h-10 mt-2 sm:hidden">
              <LogOut size={15} /> Sign out
            </button>
          </div>
        )}
      </header>

      <main className="flex-1">
        {isAnalysisPage ? (
          <Outlet />
        ) : (
          <div className="mx-auto max-w-[1240px] px-6 lg:px-10 py-10 animate-[fade-in-up_220ms_ease-out_both]">
            <Outlet />
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-[1240px] w-full px-6 lg:px-10 py-6 mt-auto border-t border-rule-200">
        <div className="flex items-center justify-between gap-4 font-mono text-[11px] text-ink-500 uppercase tracking-[0.1em]">
          <span>ReviewScope NLP analytics</span>
          <span className="normal-case">v2</span>
        </div>
      </footer>
    </div>
  );
}
