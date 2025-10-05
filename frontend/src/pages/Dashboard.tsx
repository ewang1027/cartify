import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Radio } from "lucide-react";
import { TopNavigation } from "@/components/TopNavigation";
import { BudgetCard } from "@/components/BudgetCard";
import { SustainabilityCard } from "@/components/SustainabilityCard";
import { CartItem, CartItemType } from "@/components/CartItem";
import { GlassesVideoFeed } from "@/components/GlassesVideoFeed";
import { BudgetPreferencesDialog } from "@/components/BudgetPreferencesDialog";
// import { SustainabilityMap } from "@/components/SustainabilityMap";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { fetchSustainabilityComment, playAudioFromBase64 } from "@/utils/audioUtils";
import { getCurrentLocation, formatLocation } from "@/utils/locationUtils";

type BackendCartItem = {
  name?: string;
  price?: number | string | null;
  image_url?: string | null;
  image_path?: string | null;
  sustainabilityScore?: number | null;
};

type ShoppingCartResponse = {
  shopping_cart?: Record<string, BackendCartItem>;
  cart_summary?: {
    total_price?: number;
  };
};

const API_BASE_URL = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? "http://localhost:8000";
const CART_ENDPOINT = "/shopping-cart/with-urls";
const PLACEHOLDER_IMAGE = "/placeholder.svg";

const normalizePath = (path: string): string => (path.startsWith("/") ? path : `/${path}`);

const buildImageUrl = (item: BackendCartItem): string => {
  if (item.image_url) {
    return `${API_BASE_URL}${normalizePath(item.image_url)}`;
  }

  if (item.image_path) {
    if (item.image_path.startsWith("http")) {
      return item.image_path;
    }
    return `${API_BASE_URL}${normalizePath(item.image_path)}`;
  }

  return PLACEHOLDER_IMAGE;
};

const parsePrice = (value: BackendCartItem["price"]): number => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const sanitized = value.replace(/[^0-9.]/g, "");
    const numeric = Number.parseFloat(sanitized);
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }

  return 0;
};

const deriveSustainabilityScore = (value: BackendCartItem["sustainabilityScore"]): number => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.min(100, Math.max(0, Math.round(value)));
  }

  return 75;
};

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [items, setItems] = useState<CartItemType[]>([]);
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [totalSpentExternal, setTotalSpentExternal] = useState<number | null>(null);
  const [budget, setBudget] = useState(100);
  const [sustainabilityPreference, setSustainabilityPreference] = useState<'low' | 'medium' | 'high'>('medium');
  const [showPreferencesDialog, setShowPreferencesDialog] = useState(false);
  const [hasSetPreferences, setHasSetPreferences] = useState(false);
  const [userLocation, setUserLocation] = useState<string>('');

  const totalSpent = useMemo(() => (
    totalSpentExternal ?? items.reduce((sum, item) => sum + item.price, 0)
  ), [items, totalSpentExternal]);
  const avgSustainability = items.length > 0
    ? Math.round(items.reduce((sum, item) => sum + item.sustainabilityScore, 0) / items.length)
    : 0;

  const fetchCartData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}${CART_ENDPOINT}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch cart: ${response.status}`);
      }

      const data: ShoppingCartResponse = await response.json();
      const shoppingCart = data.shopping_cart ?? {};
      const cartItems: CartItemType[] = Object.entries(shoppingCart).map(([id, item]) => ({
        id,
        name: item.name ?? "Unknown item",
        price: parsePrice(item.price),
        image: buildImageUrl(item),
        sustainabilityScore: deriveSustainabilityScore(item.sustainabilityScore),
      }));

      setItems(cartItems);

      if (data.cart_summary && typeof data.cart_summary.total_price === "number") {
        setTotalSpentExternal(data.cart_summary.total_price);
      } else {
        setTotalSpentExternal(null);
      }
    } catch (error) {
      console.error("Error fetching cart data:", error);
    }
  }, []);

  useEffect(() => {
    fetchCartData();
    const intervalId = window.setInterval(fetchCartData, 2000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [fetchCartData]);

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

  // Show preferences dialog only when coming from home page, not from Analytics
  useEffect(() => {
    const isComingFromAnalytics = location.state?.from === 'analytics';
    if (!isComingFromAnalytics) {
      setShowPreferencesDialog(true);
    }
  }, [location.state]);

  // Fetch user location on component mount
  useEffect(() => {
    const fetchLocation = async () => {
      try {
        const locationData = await getCurrentLocation();
        const formattedLocation = formatLocation(locationData);
        setUserLocation(formattedLocation);
      } catch (error) {
        console.error('Error fetching location:', error);
        setUserLocation('Location unavailable');
      }
    };

    fetchLocation();
  }, []);

  const handleRemoveItem = (id: string) => {
    setItems(items.filter(item => item.id !== id));
    toast.info("Item removed from cart");
  };

  const handleSyncToggle = (checked: boolean) => {
    setSyncEnabled(checked);
    if (checked) {
      toast.info("Glasses camera enabled", {
        description: "Camera access requested for glasses view...",
      });
    } else {
      toast.info("Glasses camera disabled");
    }
  };

  const handleSavePreferences = async (newBudget: number, newSustainabilityPreference: 'low' | 'medium' | 'high') => {
    setBudget(newBudget);
    setSustainabilityPreference(newSustainabilityPreference);
    setHasSetPreferences(true);
    
    const preferenceLabel = newSustainabilityPreference === 'high' ? 'Eco Conscious' : 
                           newSustainabilityPreference === 'medium' ? 'Balanced' : 'Budget Focused';
    
    toast.success("Preferences updated!", {
      description: `Budget: $${newBudget} • ${preferenceLabel}`
    });

    // Play ElevenLabs audio comment
    try {
      const audioData = await fetchSustainabilityComment(newSustainabilityPreference);
      
      if (audioData.success && audioData.audio) {
        await playAudioFromBase64(audioData.audio);
      } else {
        // Fallback: show the comment as text if audio fails
        console.log("Audio generation failed, showing text comment:", audioData.comment);
        toast.info("Great choice!", {
          description: audioData.comment
        });
      }
    } catch (error) {
      console.error("Error playing audio comment:", error);
      // Silently fail - don't interrupt the user experience
    }
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
      <TopNavigation username="Manoj" budget={budget} location={userLocation} />
      
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
                  <Label htmlFor="sync" className="text-sm font-medium">Glasses Camera</Label>
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
                    Add items using the button above or enable glasses camera
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

            {/* Sustainability Map */}
            {/* <SustainabilityMap currentSustainabilityScore={avgSustainability} /> */}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
