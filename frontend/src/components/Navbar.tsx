import { ShoppingCart } from "lucide-react";

interface NavbarProps {
  username?: string;
  budget?: number;
  location?: string;
}

export const Navbar = ({ username = "Guest", budget = 0, location }: NavbarProps) => {
  return (
    <nav className="bg-card border-b border-border px-6 py-4 shadow-sm">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-hero rounded-lg">
            <ShoppingCart className="w-6 h-6 text-primary-foreground" />
          </div>
          <span className="text-xl font-semibold text-foreground">Cartify</span>
        </div>
        
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
    </nav>
  );
};
