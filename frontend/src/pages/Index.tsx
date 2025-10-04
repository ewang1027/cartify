import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShoppingCart, Glasses, TrendingUp, Leaf } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
// import heroImage from "@/assets/hero-bg.jpg";

const Index = () => {
  const navigate = useNavigate();
  const [showLearnMore, setShowLearnMore] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* Background Image with Overlay */}
        <div className="absolute inset-0 z-0">
          <div 
            className="absolute inset-0 bg-cover bg-center"
            // style={{ backgroundImage: `url(${heroImage})` }}
          />
          <div className="absolute inset-0 bg-background/90" />
        </div>

        {/* Content */}
        <div className="relative z-10 container mx-auto px-6 text-center animate-fade-in max-w-4xl">
          <div className="mb-12 inline-flex items-center gap-2 animate-scale-in">
            <div className="p-2.5 bg-gradient-hero rounded-xl">
              <ShoppingCart className="w-7 h-7 text-primary-foreground" />
            </div>
            <span className="text-3xl font-bold text-foreground">Cartify</span>
          </div>

          <h1 className="text-6xl md:text-7xl font-bold text-foreground mb-8 leading-tight tracking-tight">
            Shop Smart.<br />
            Spend Wisely.<br />
            <span className="bg-gradient-hero bg-clip-text text-transparent">Live Sustainably.</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-12">
            Track spending and eco-impact with Ray-Ban Meta glasses
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-20">
            <Button
              onClick={() => navigate("/dashboard")}
              size="lg"
              className="bg-gradient-hero text-primary-foreground shadow-soft hover:shadow-lg transition-all px-8 py-6"
            >
              <Glasses className="w-5 h-5 mr-2" />
              Connect Glasses
            </Button>
            <Button
              onClick={() => setShowLearnMore(true)}
              variant="outline"
              size="lg"
              className="px-8 py-6 border-2"
            >
              Learn More
            </Button>
          </div>

          {/* Feature Highlights */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="p-8 bg-card rounded-2xl border border-border shadow-card hover:shadow-soft transition-all group">
              <TrendingUp className="w-10 h-10 text-primary mb-4 mx-auto group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-semibold text-foreground mb-2">Budget Tracking</h3>
              <p className="text-sm text-muted-foreground">Real-time spending alerts</p>
            </div>

            <div className="p-8 bg-card rounded-2xl border border-border shadow-card hover:shadow-soft transition-all group">
              <Leaf className="w-10 h-10 text-primary mb-4 mx-auto group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-semibold text-foreground mb-2">Eco Score</h3>
              <p className="text-sm text-muted-foreground">Track environmental impact</p>
            </div>

            <div className="p-8 bg-card rounded-2xl border border-border shadow-card hover:shadow-soft transition-all group">
              <Glasses className="w-10 h-10 text-primary mb-4 mx-auto group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-semibold text-foreground mb-2">Smart Sync</h3>
              <p className="text-sm text-muted-foreground">Seamless glasses integration</p>
            </div>
          </div>
        </div>
      </section>

      {/* Learn More Dialog */}
      <Dialog open={showLearnMore} onOpenChange={setShowLearnMore}>
        <DialogContent className="max-w-2xl bg-gradient-card border-border">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-foreground">How It Works</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Three simple steps
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            <div className="flex gap-4 items-start p-5 bg-card rounded-xl border border-border">
              <div className="w-10 h-10 bg-gradient-hero rounded-lg flex items-center justify-center flex-shrink-0 text-primary-foreground font-bold">
                1
              </div>
              <div>
                <h4 className="font-semibold text-foreground mb-1">Connect Glasses</h4>
                <p className="text-sm text-muted-foreground">
                  Pair your Ray-Ban Meta smart glasses with Cartify.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start p-5 bg-card rounded-xl border border-border">
              <div className="w-10 h-10 bg-gradient-hero rounded-lg flex items-center justify-center flex-shrink-0 text-primary-foreground font-bold">
                2
              </div>
              <div>
                <h4 className="font-semibold text-foreground mb-1">Add Items</h4>
                <p className="text-sm text-muted-foreground">
                  Your glasses identify products and add them to your cart automatically.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start p-5 bg-card rounded-xl border border-border">
              <div className="w-10 h-10 bg-gradient-hero rounded-lg flex items-center justify-center flex-shrink-0 text-primary-foreground font-bold">
                3
              </div>
              <div>
                <h4 className="font-semibold text-foreground mb-1">Track & Save</h4>
                <p className="text-sm text-muted-foreground">
                  Monitor spending and environmental impact in real-time.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <Button
              onClick={() => {
                setShowLearnMore(false);
                navigate("/dashboard");
              }}
              className="bg-gradient-hero text-primary-foreground shadow-soft"
            >
              Get Started
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Index;
