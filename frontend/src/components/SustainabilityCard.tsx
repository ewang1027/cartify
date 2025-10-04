import { Leaf } from "lucide-react";
import { Card } from "@/components/ui/card";

interface SustainabilityCardProps {
  score: number; // 0-100
}

export const SustainabilityCard = ({ score }: SustainabilityCardProps) => {
  const getGrade = (score: number): string => {
    if (score >= 90) return "A";
    if (score >= 80) return "B";
    if (score >= 70) return "C";
    if (score >= 60) return "D";
    return "E";
  };

  const getColorClass = () => {
    if (score >= 80) return "text-success";
    if (score >= 60) return "text-warning";
    return "text-destructive";
  };

  const getBgColor = () => {
    if (score >= 80) return "bg-success";
    if (score >= 60) return "bg-warning";
    return "bg-destructive";
  };

  const grade = getGrade(score);
  const isEcoHero = score >= 80;

  return (
    <Card className="p-6 bg-gradient-card shadow-card animate-fade-in">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground mb-1">Sustainability Score</h3>
          <p className="text-sm text-muted-foreground">Eco-friendly choices</p>
        </div>
        <Leaf className={`w-6 h-6 ${getColorClass()}`} />
      </div>

      <div className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className={`text-5xl font-bold ${getColorClass()}`}>
            {grade}
          </span>
          <span className="text-xl text-muted-foreground">({score}%)</span>
        </div>

        <div className="space-y-2">
          <div className="flex gap-1">
            {['A', 'B', 'C', 'D', 'E'].map((g, i) => (
              <div
                key={g}
                className={`flex-1 h-2 rounded-full transition-all duration-300 ${
                  ['A', 'B', 'C', 'D', 'E'].indexOf(grade) >= i
                    ? getBgColor()
                    : 'bg-muted'
                }`}
              />
            ))}
          </div>
          <p className="text-sm text-muted-foreground">
            Your cart is {score}% sustainable 🌱
          </p>
        </div>

        {isEcoHero && (
          <div className="mt-4 p-3 bg-success/10 border border-success/20 rounded-lg">
            <p className="text-sm font-medium text-success">
              🌿 Eco Hero! Keep up the great choices!
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
