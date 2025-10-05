import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Radio } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { BudgetCard } from "@/components/BudgetCard";
import { SustainabilityCard } from "@/components/SustainabilityCard";
import { CartItem, CartItemType } from "@/components/CartItem";
import { GlassesVideoFeed } from "@/components/GlassesVideoFeed";
import { BudgetPreferencesDialog } from "@/components/BudgetPreferencesDialog";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

// Mock data for testing
const MOCK_ITEMS: CartItemType[] = [
  {
    id: '1',
    name: 'Organic Bananas',
    price: 3.99,
    image: 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=150&h=150&fit=crop',
    sustainabilityScore: 85
  },
  {
    id: '2',
    name: 'Local Honey',
    price: 8.99,
    image: 'https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=150&h=150&fit=crop',
    sustainabilityScore: 90
  },
  {
    id: '3',
    name: 'Plastic Water Bottle',
    price: 1.99,
    image: 'https://images.unsplash.com/photo-1583394838336-acd977736f90?w=150&h=150&fit=crop',
    sustainabilityScore: 15
  },
  {
    id: '4',
    name: 'Fair Trade Coffee',
    price: 12.99,
    image: 'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=150&h=150&fit=crop',
    sustainabilityScore: 75
  },
  {
    id: '5',
    name: 'Bamboo Toothbrush',
    price: 4.99,
    image: 'https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=150&h=150&fit=crop',
    sustainabilityScore: 95
  }
];

const Dashboard = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<CartItemType[]>([]);
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [budget, setBudget] = useState(100);
  const [sustainabilityPreference, setSustainabilityPreference] = useState<'low' | 'medium' | 'high'>('medium');
  const [showPreferencesDialog, setShowPreferencesDialog] = useState(false);
  const [hasSetPreferences, setHasSetPreferences] = useState(false);

  const totalSpent = items.reduce((sum, item) => sum + item.price, 0);
  const avgSustainability = items.length > 0
    ? Math.round(items.reduce((sum, item) => sum + item.sustainabilityScore, 0) / items.length)
    : 0;

  useEffect(() => {
    if (totalSpent > budget) {
      toast.error(`Budget Exceeded 💸`, {
        description: `You're over budget by $${(totalSpent - budget).toFixed(2)}`,
      });
    }
  }, [totalSpent, budget]);

  useEffect(() => {
    if (avgSustainability >= 80 && items.length > 0) {
      toast.success("Eco Hero 🌿", {
        description: "Your cart is 80%+ sustainable!",
      });
    }
  }, [avgSustainability, items.length]);

  // Show preferences dialog every time user enters dashboard
  useEffect(() => {
    setShowPreferencesDialog(true);
  }, []);

  const handleRemoveItem = (id: string) => {
    setItems(items.filter(item => item.id !== id));
    toast.info("Item removed from cart");
  };

  const handleAddMockItem = () => {
    const availableItems = MOCK_ITEMS.filter(
      mockItem => !items.find(item => item.id === mockItem.id)
    );
    
    if (availableItems.length === 0) {
      toast.info("All mock items already in cart");
      return;
    }

    const randomItem = availableItems[Math.floor(Math.random() * availableItems.length)];
    setItems([...items, randomItem]);
    toast.success("Item added to cart", {
      description: randomItem.name,
    });
  };

  const handleSyncToggle = (checked: boolean) => {
    setSyncEnabled(checked);
    if (checked) {
      toast.info("Glasses sync enabled", {
        description: "Now looking for grocery products...",
      });
    } else {
      toast.info("Glasses sync disabled");
    }
  };

  const handleSavePreferences = (newBudget: number, newSustainabilityPreference: 'low' | 'medium' | 'high') => {
    setBudget(newBudget);
    setSustainabilityPreference(newSustainabilityPreference);
    setHasSetPreferences(true);
    
    toast.success("Preferences updated!", {
      description: `Budget: $${newBudget} • ${newSustainabilityPreference === 'high' ? 'Eco Conscious' : newSustainabilityPreference === 'medium' ? 'Balanced' : 'Budget Focused'}`
    });
  };

  const handleClosePreferencesDialog = () => {
    setShowPreferencesDialog(false);
    if (!hasSetPreferences) {
      // If user closes without setting preferences, use defaults
      setHasSetPreferences(true);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar username="Manoj" budget={budget} />
      
      {/* Preferences Dialog */}
      <BudgetPreferencesDialog
        isOpen={showPreferencesDialog}
        onSave={handleSavePreferences}
        onClose={handleClosePreferencesDialog}
      />
      
      <main className="container mx-auto px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Left Column - Video Feed */}
          <div className="lg:w-80 flex-shrink-0">
            <div className="sticky top-8">
              <GlassesVideoFeed isActive={syncEnabled} />
            </div>
          </div>

          {/* Right Column - Main Content */}
          <div className="flex-1 space-y-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
                <p className="text-muted-foreground">Track your cart in real-time</p>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-4 py-2 bg-card rounded-lg border border-border">
                  <Radio className={`w-4 h-4 ${syncEnabled ? 'text-success animate-pulse' : 'text-muted-foreground'}`} />
                  <Label htmlFor="sync" className="text-sm font-medium">Sync with Glasses</Label>
                  <Switch
                    id="sync"
                    checked={syncEnabled}
                    onCheckedChange={handleSyncToggle}
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <BudgetCard spent={totalSpent} budget={budget} />
              <SustainabilityCard score={avgSustainability} />
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold text-foreground">
                  Current Items in Cart
                  {items.length > 0 && (
                    <span className="ml-3 text-lg text-muted-foreground">({items.length})</span>
                  )}
                </h2>
              </div>

              {items.length === 0 ? (
                <div className="text-center py-16 bg-card rounded-lg border border-dashed border-border">
                  <p className="text-muted-foreground text-lg mb-4">Your cart is empty</p>
                  <p className="text-sm text-muted-foreground mb-6">
                    Add items using the button above or enable glasses sync
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => navigate("/")}
                  >
                    Back to Home
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {items.map((item) => (
                    <CartItem key={item.id} item={item} onRemove={handleRemoveItem} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
