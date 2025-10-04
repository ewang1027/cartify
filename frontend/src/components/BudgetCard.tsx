import { TrendingUp, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";

interface BudgetCardProps {
  spent: number;
  budget: number;
}

export const BudgetCard = ({ spent, budget }: BudgetCardProps) => {
  const percentage = Math.min((spent / budget) * 100, 100);
  const isOverBudget = spent > budget;
  
  const getColorClass = () => {
    if (isOverBudget) return "text-destructive";
    if (percentage > 80) return "text-warning";
    return "text-success";
  };

  const getProgressColor = () => {
    if (isOverBudget) return "bg-destructive";
    if (percentage > 80) return "bg-warning";
    return "bg-success";
  };

  return (
    <Card className="p-6 bg-gradient-card shadow-card animate-fade-in">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground mb-1">Budget Overview</h3>
          <p className="text-sm text-muted-foreground">Track your spending</p>
        </div>
        {isOverBudget ? (
          <AlertCircle className="w-6 h-6 text-destructive" />
        ) : (
          <TrendingUp className={`w-6 h-6 ${getColorClass()}`} />
        )}
      </div>

      <div className="space-y-4">
        <div className="flex items-baseline justify-between">
          <span className={`text-4xl font-bold ${getColorClass()}`}>
            ${spent.toFixed(2)}
          </span>
          <span className="text-xl text-muted-foreground">/ ${budget.toFixed(2)}</span>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className={`font-semibold ${getColorClass()}`}>
              {percentage.toFixed(0)}%
            </span>
          </div>
          <div className="h-3 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full ${getProgressColor()} transition-all duration-500 rounded-full`}
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
        </div>

        {isOverBudget && (
          <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm font-medium text-destructive">
              ⚠️ Budget Exceeded by ${(spent - budget).toFixed(2)}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
