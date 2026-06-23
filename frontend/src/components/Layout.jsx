import React, { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";

const NAV = {
  owner: [
    { to: "/",            label: "Dashboard",     icon: "📊", section: "Overview" },
    { to: "/students",    label: "Students",      icon: "🎓", section: "Operations" },
    { to: "/teachers",    label: "Teachers",      icon: "👨‍🏫", section: "Operations" },
    { to: "/records",     label: "Records",       icon: "🗂", section: "Operations" },
    { to: "/approvals",   label: "Approvals",     icon: "✅", section: "Operations" },
    { to: "/fees",        label: "Fees",          icon: "💳", section: "Operations" },
    { to: "/expenses",    label: "Expenses",      icon: "🧾", section: "Operations" },
    { to: "/marks",       label: "Marks & Exams", icon: "📝", section: "Academics" },
    { to: "/attendance",  label: "Attendance",    icon: "🗓", section: "Academics" },
    { to: "/timetable",   label: "Timetable",     icon: "📅", section: "Academics" },
    { to: "/finance",     label: "Finance",       icon: "🏦", section: "Money" },
    { to: "/reports",     label: "Reports",       icon: "📈", section: "Money" },
    { to: "/tiles",       label: "Quick Tiles",   icon: "🔲", section: "Admin" },
    { to: "/assistant",   label: "Assistant",     icon: "💬", section: "Admin" },
    { to: "/scanner",     label: "Scanner",       icon: "🔍", section: "Admin" },
    { to: "/audit",       label: "Audit Log",     icon: "📜", section: "Admin" },
    { to: "/notifications", label: "Notifications", icon: "📬", section: "Admin" },
    { to: "/settings",    label: "Settings",      icon: "⚙️", section: "Admin" },
  ],
  staff: [
    { to: "/",         label: "Quick Entry", icon: "⚡", section: "Today" },
    { to: "/students", label: "Students",    icon: "🎓", section: "Today" },
    { to: "/settings", label: "Settings",    icon: "⚙️", section: "Account" },
  ],
  teacher: [
    { to: "/",            label: "Dashboard",   icon: "📊", section: "Today" },
    { to: "/my-classes",  label: "My Classes",  icon: "🎓", section: "Today" },
    { to: "/attendance",  label: "Attendance",  icon: "🗓", section: "Today" },
    { to: "/timetable",   label: "Timetable",   icon: "📅", section: "Today" },
    { to: "/assignments", label: "Assignments", icon: "📝", section: "Academics" },
    { to: "/quick-entry", label: "Quick Entry", icon: "⚡", section: "Front Office", flagged: "frontoffice" },
    { to: "/settings",    label: "Settings",    icon: "⚙️", section: "Account" },
  ],
  student: [
    { to: "/",            label: "Dashboard",    icon: "📊", section: "Today" },
    { to: "/my-marks",    label: "My Marks",     icon: "📈", section: "Academics" },
    { to: "/my-attendance", label: "My Attendance", icon: "🗓", section: "Academics" },
    { to: "/my-timetable", label: "My Timetable", icon: "📅", section: "Academics" },
    { to: "/my-assignments", label: "Assignments", icon: "📝", section: "Academics" },
    { to: "/games",       label: "Mind Games",   icon: "🎮", section: "Fun" },
    { to: "/settings",    label: "Settings",     icon: "⚙️", section: "Account" },
  ],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  // Close drawer on route change (mobile)
  useEffect(() => { setOpen(false); }, [location.pathname]);

  let items = NAV[user?.role] || [];
  if (user?.role === "teacher" && !user.can_do_front_office) {
    items = items.filter((it) => it.flagged !== "frontoffice");
  }

  const sections = items.reduce((acc, it) => {
    (acc[it.section] = acc[it.section] || []).push(it);
    return acc;
  }, {});

  const currentLabel = items.find((it) =>
    it.to === "/" ? location.pathname === "/" : location.pathname.startsWith(it.to)
  )?.label || "Dashboard";

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <div className="app-shell">
      {/* Mobile top bar */}
      <header className="topbar">
        <button className="hamburger" onClick={() => setOpen(true)} aria-label="Open menu">☰</button>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="brand-mark" style={{ width: 30, height: 30, fontSize: 13 }}>S</div>
          <div className="topbar-title">{currentLabel}</div>
        </div>
      </header>

      {/* Backdrop (mobile only when sidebar is open) */}
      <div className={"sidebar-backdrop" + (open ? " open" : "")}
           onClick={() => setOpen(false)}/>

      <aside className={"sidebar" + (open ? " open" : "")}>
        <div className="brand">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-name">Sage</div>
            <div className="brand-sub">AI-first School ERP · K–10</div>
          </div>
        </div>

        <nav className="nav">
          {Object.entries(sections).map(([section, list]) => (
            <React.Fragment key={section}>
              <div className="nav-section">{section}</div>
              {list.map((it) => (
                <NavLink
                  key={it.to}
                  to={it.to}
                  end={it.to === "/"}
                  className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
                >
                  <span className="icon">{it.icon}</span>
                  {it.label}
                </NavLink>
              ))}
            </React.Fragment>
          ))}
        </nav>

        <div className="user-card">
          <div className="avatar">{(user?.name || "?").slice(0, 1).toUpperCase()}</div>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div className="name" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {user?.name}
            </div>
            <div className="role">{user?.role}</div>
          </div>
          <button className="btn btn-secondary"
                  style={{ padding: "8px 12px", fontSize: 12, minHeight: "auto" }}
                  onClick={handleLogout} title="Sign out">↩</button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
