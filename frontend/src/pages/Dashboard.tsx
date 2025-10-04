import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Radio } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { BudgetCard } from "@/components/BudgetCard";
import { SustainabilityCard } from "@/components/SustainabilityCard";
import { CartItem, CartItemType } from "@/components/CartItem";
import { GlassesVideoFeed } from "@/components/GlassesVideoFeed";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const MOCK_ITEMS: CartItemType[] = [
  {
    id: "1",
    name: "Organic Bananas",
    price: 3.99,
    image: "https://images.unsplash.com/photo-1603833665858-e61d17a86224?w=200&h=200&fit=crop",
    sustainabilityScore: 95,
  },
  {
    id: "2",
    name: "Whole Grain Bread",
    price: 4.49,
    image: "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=200&h=200&fit=crop",
    sustainabilityScore: 85,
  },
  {
    id: "3",
    name: "Almond Milk",
    price: 5.99,
    image: "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=200&h=200&fit=crop",
    sustainabilityScore: 78,
  },
];

const Dashboard = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<CartItemType[]>([]);
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [budget] = useState(100);

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
        description: "Now listening for products...",
      });
    } else {
      toast.info("Glasses sync disabled");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar username="Alex Morgan" budget={budget} />
      
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
                <Button
                  onClick={handleAddMockItem}
                  className="bg-gradient-hero text-primary-foreground shadow-soft hover:shadow-md transition-all"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Item
                </Button>
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
