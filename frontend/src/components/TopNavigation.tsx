import { Link, useLocation, useNavigate } from "react-router-dom";
import { BarChart3, LayoutDashboard } from "lucide-react";
import { cn } from "@/lib/utils";

interface TopNavigationProps {
  username?: string;
  budget?: number;
  location?: string;
}

export const TopNavigation = ({ username = "Guest", budget = 0, location }: TopNavigationProps) => {
  const location_path = useLocation();
  const navigate = useNavigate();

  const navItems = [
    {
      name: "Dashboard",
      path: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Analytics",
      path: "/analytics",
      icon: BarChart3,
    },
  ];

  return (
    <div className="bg-card border-b border-border shadow-sm">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-hero rounded-lg">
              <LayoutDashboard className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">Cartify</span>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location_path.pathname === item.path;
              
              const handleNavigation = (e: React.MouseEvent) => {
                e.preventDefault();
                if (item.path === "/dashboard" && location_path.pathname === "/analytics") {
                  navigate(item.path, { state: { from: "analytics" } });
                } else {
                  navigate(item.path);
                }
              };
              
              return (
                <button
                  key={item.path}
                  onClick={handleNavigation}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.name}
                </button>
              );
            })}
          </nav>

          {/* User Info */}
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Budget</p>
              <p className="text-lg font-semibold text-foreground">${budget.toFixed(2)}</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-full bg-gradient-hero flex items-center justify-center text-primary-foreground font-semibold">
                {username.charAt(0).toUpperCase()}
              </div>
              <div className="text-right">
                <span className="text-sm font-medium text-foreground block">{username}</span>
                {location && (
                  <span className="text-xs text-muted-foreground">{location}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
