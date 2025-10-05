import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { DollarSign, Leaf, Zap, Thermometer, Apple } from "lucide-react";

interface BudgetPreferencesDialogProps {
  isOpen: boolean;
  onSave: (budget: number, sustainabilityLevel: 'low' | 'medium' | 'high', sustainabilityEnabled: boolean, nutritionalValueEnabled: boolean) => void;
  onClose: () => void;
}

const sustainabilityLevels = {
  low: { 
    label: 'Budget Focused', 
    description: 'Prioritize savings and deals',
    icon: DollarSign,
    color: 'text-yellow-500'
  },
  medium: { 
    label: 'Balanced', 
    description: 'Balance cost and sustainability',
    icon: Zap,
    color: 'text-blue-500'
  },
  high: { 
    label: 'Eco Conscious', 
    description: 'Prioritize environmental impact',
    icon: Leaf,
    color: 'text-green-500'
  }
} as const;

export const BudgetPreferencesDialog = ({ isOpen, onSave, onClose }: BudgetPreferencesDialogProps) => {
  const [budget, setBudget] = useState(100);
  const [sustainabilityLevel, setSustainabilityLevel] = useState<'low' | 'medium' | 'high'>('medium');
  const [sustainabilityEnabled, setSustainabilityEnabled] = useState(true);
  const [nutritionalValueEnabled, setNutritionalValueEnabled] = useState(true);
  const [isValid, setIsValid] = useState(false);

  useEffect(() => {
    setIsValid(budget > 0 && budget <= 10000);
  }, [budget]);

  const handleSave = () => {
    if (isValid) {
      onSave(budget, sustainabilityLevel, sustainabilityEnabled, nutritionalValueEnabled);
      onClose();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isValid) {
      handleSave();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Thermometer className="w-5 h-5 text-primary" />
            Set Your Preferences
          </DialogTitle>
          <DialogDescription>
            Tell us about your budget and sustainability preferences to personalize your shopping experience.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Budget Input */}
          <div className="space-y-3">
            <Label htmlFor="budget" className="text-sm font-medium">
              Shopping Budget ($)
            </Label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="budget"
                type="number"
                min="1"
                max="10000"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                onKeyPress={handleKeyPress}
                className="pl-10"
                placeholder="Enter your budget"
              />
            </div>
            {!isValid && budget > 0 && (
              <p className="text-xs text-red-500">
                Budget must be between $1 and $10,000
              </p>
            )}
          </div>

          {/* Sustainability Level Selection */}
          {/* <div className="space-y-3">
            <Label className="text-sm font-medium">
              Sustainability Preference
            </Label>
            <div className="space-y-3">
              {(Object.entries(sustainabilityLevels) as [keyof typeof sustainabilityLevels, typeof sustainabilityLevels[keyof typeof sustainabilityLevels]][]).map(([key, level]) => {
                const Icon = level.icon;
                const isSelected = sustainabilityLevel === key;
                
                return (
                  <Card 
                    key={key}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      isSelected 
                        ? 'ring-2 ring-primary bg-primary/5' 
                        : 'hover:bg-muted/50'
                    }`}
                    onClick={() => setSustainabilityLevel(key)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <Icon className={`w-5 h-5 ${level.color}`} />
                        <div className="flex-1">
                          <h4 className="font-medium text-sm">{level.label}</h4>
                          <p className="text-xs text-muted-foreground">{level.description}</p>
                        </div>
                        <div className={`w-4 h-4 rounded-full border-2 ${
                          isSelected 
                            ? 'border-primary bg-primary' 
                            : 'border-muted-foreground'
                        }`}>
                          {isSelected && (
                            <div className="w-full h-full rounded-full bg-background scale-50" />
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div> */}

          {/* Preference Toggles */}
          <div className="space-y-4">
            <Label className="text-sm font-medium">
              Enable Features
            </Label>
            
            {/* Sustainability Toggle */}
            <div className="flex items-center justify-between p-4 bg-card rounded-lg border border-border">
              <div className="flex items-center gap-3">
                <Leaf className="w-5 h-5 text-green-500" />
                <div>
                  <h4 className="font-medium text-sm">Sustainability Tracking</h4>
                  <p className="text-xs text-muted-foreground">Track environmental impact of your purchases</p>
                </div>
              </div>
              <Switch
                checked={sustainabilityEnabled}
                onCheckedChange={setSustainabilityEnabled}
              />
            </div>

            {/* Nutritional Value Toggle */}
            <div className="flex items-center justify-between p-4 bg-card rounded-lg border border-border">
              <div className="flex items-center gap-3">
                <Apple className="w-5 h-5 text-orange-500" />
                <div>
                  <h4 className="font-medium text-sm">Nutritional Value</h4>
                  <p className="text-xs text-muted-foreground">Get nutrition information for food items</p>
                </div>
              </div>
              <Switch
                checked={nutritionalValueEnabled}
                onCheckedChange={setNutritionalValueEnabled}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              Skip for Now
            </Button>
            <Button
              onClick={handleSave}
              disabled={!isValid}
              className="flex-1"
            >
              Save Preferences
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
