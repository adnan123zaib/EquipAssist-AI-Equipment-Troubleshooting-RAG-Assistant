import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, BookOpen, Settings, Menu } from 'lucide-react';
import './Sidebar.css';

const links = [
  ['/app', LayoutDashboard, 'Dashboard'],
  ['/app/chat', MessageSquare, 'Troubleshooting Chat'],
  ['/app/manuals', BookOpen, 'Manuals'],
  ['/app/settings', Settings, 'Settings'],
];

export default function Sidebar({ open, setOpen }) {
  return (
    <>
      <button
        className="mobile-menu"
        aria-label="Open menu"
        onClick={() => setOpen(!open)}
      >
        <Menu />
      </button>

      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <span>EA</span>
          <b>EquipAssist AI</b>
        </div>

        <nav>
          {links.map(([to, I, label]) => (
            <NavLink
              end={to === '/app'}
              to={to}
              key={to}
              onClick={() => setOpen(false)}
            >
              <I size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}