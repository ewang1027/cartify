import { X, Leaf } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface CartItemType {
  id: string;
  name: string;
  price: number;
  image: string;
  sustainabilityScore: number; // 0-100
}

interface CartItemProps {
  item: CartItemType;
  onRemove: (id: string) => void;
}

export const CartItem = ({ item, onRemove }: CartItemProps) => {
  const getLeafCount = (score: number): number => {
    if (score >= 80) return 5;
    if (score >= 60) return 4;
    if (score >= 40) return 3;
    if (score >= 20) return 2;
    return 1;
  };

  const leafCount = getLeafCount(item.sustainabilityScore);

  return (
    <Card className="p-4 bg-card shadow-sm hover:shadow-md transition-all duration-200 animate-slide-up">
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-lg overflow-hidden bg-muted flex-shrink-0">
          <img 
            src={item.image} 
            alt={item.name}
            className="w-full h-full object-cover"
          />
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-foreground truncate">{item.name}</h4>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex gap-0.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <Leaf
                  key={i}
                  className={`w-3 h-3 ${
                    i < leafCount ? 'text-success fill-success' : 'text-muted'
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-muted-foreground">
              {item.sustainabilityScore}%
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-foreground">
            ${item.price.toFixed(2)}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onRemove(item.id)}
            className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
};
