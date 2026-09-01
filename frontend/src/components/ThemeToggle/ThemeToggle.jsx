import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import './ThemeToggle.css';

export default function ThemeToggle({ compact = false }) {
  const { theme, toggleTheme } = useTheme();

  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      className={`theme-toggle ${compact ? 'compact' : ''}`}
      onClick={toggleTheme}
      aria-label={isDark ? 'Dark mode' : 'Light mode'}
      title={isDark ? 'Dark mode' : 'Light mode'}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}

      <span>
        {isDark ? 'Dark mode' : 'Light mode'}
      </span>
    </button>
  );
}