import { BarChart3, RotateCcw, Moon, Sun } from 'lucide-react'

function Header({ hasFile, onReset, darkMode, onToggleDarkMode }) {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-gray-900/80 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white leading-tight">
                ReviewScope
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-tight hidden sm:block">
                AI-Powered Feedback Intelligence
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onToggleDarkMode}
              className="p-2 rounded-xl text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={darkMode ? 'Light mode' : 'Dark mode'}
            >
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {hasFile && (
              <button onClick={onReset} className="btn-secondary text-sm">
                <RotateCcw className="w-4 h-4" />
                <span className="hidden sm:inline">New Analysis</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
