import { useState, useEffect } from "react";
import { TopNavigation } from "@/components/TopNavigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Trophy, Target, Leaf, TrendingUp, Users, Award, Flame } from "lucide-react";
import { getCurrentLocation, formatLocation } from "@/utils/locationUtils";

interface LeaderboardUser {
  id: string;
  name: string;
  score: number;
  sustainabilityScore: number;
  avatar: string;
  rank: number;
}

interface Challenge {
  id: string;
  title: string;
  description: string;
  points: number;
  completed: boolean;
  progress: number;
  maxProgress: number;
}

const Analytics = () => {
  const [userLocation, setUserLocation] = useState<string>('');
  const [budget] = useState(100); // This would come from context/state management

  // Mock data for leaderboard
  const [leaderboard] = useState<LeaderboardUser[]>([
    { id: "1", name: "EcoWarrior23", score: 1250, sustainabilityScore: 95, avatar: "E", rank: 1 },
    { id: "2", name: "GreenGrocery", score: 1180, sustainabilityScore: 92, avatar: "G", rank: 2 },
    { id: "3", name: "SustainableSam", score: 1100, sustainabilityScore: 88, avatar: "S", rank: 3 },
    { id: "4", name: "Manoj", score: 950, sustainabilityScore: 85, avatar: "M", rank: 4 },
    { id: "5", name: "EcoFriendly", score: 875, sustainabilityScore: 82, avatar: "E", rank: 5 },
  ]);

  // Mock data for challenges
  const [challenges] = useState<Challenge[]>([
    {
      id: "1",
      title: "Green Shopping Spree",
      description: "Buy 10 sustainable products this month",
      points: 100,
      completed: false,
      progress: 7,
      maxProgress: 10,
    },
    {
      id: "2",
      title: "Budget Master",
      description: "Stay within budget for 5 consecutive shopping trips",
      points: 150,
      completed: false,
      progress: 3,
      maxProgress: 5,
    },
    {
      id: "3",
      title: "Eco Hero",
      description: "Achieve 90% sustainability score in one cart",
      points: 200,
      completed: true,
      progress: 1,
      maxProgress: 1,
    },
    {
      id: "4",
      title: "Consistent Saver",
      description: "Save $50 or more per month for 3 months",
      points: 300,
      completed: false,
      progress: 1,
      maxProgress: 3,
    },
  ]);

  const sustainabilityStreak = 12; // Mock streak data
  const totalPoints = 950; // Mock total points

  // Fetch user location
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

  const completedChallenges = challenges.filter(c => c.completed).length;
  const totalChallenges = challenges.length;

  return (
    <div className="min-h-screen bg-background">
      <TopNavigation username="Manoj" budget={budget} location={userLocation} />
      
      <main className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Analytics</h1>
          <p className="text-muted-foreground">Track your sustainability journey and compete with others</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - User Stats */}
          <div className="lg:col-span-1 space-y-6">
            {/* Sustainability Streak */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Flame className="w-5 h-5 text-orange-500" />
                  Sustainability Streak
                </CardTitle>
                <CardDescription>
                  Consecutive days of sustainable shopping
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className="text-4xl font-bold text-orange-500 mb-2">
                    {sustainabilityStreak}
                  </div>
                  <p className="text-sm text-muted-foreground">days</p>
                  <Badge variant="secondary" className="mt-3">
                    <TrendingUp className="w-3 h-3 mr-1" />
                    +3 this week
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* Total Points */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Award className="w-5 h-5 text-yellow-500" />
                  Total Points
                </CardTitle>
                <CardDescription>
                  Earned through challenges and sustainable shopping
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className="text-4xl font-bold text-yellow-500 mb-2">
                    {totalPoints}
                  </div>
                  <p className="text-sm text-muted-foreground">points</p>
                </div>
              </CardContent>
            </Card>

            {/* Challenge Progress */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Target className="w-5 h-5 text-blue-500" />
                  Challenge Progress
                </CardTitle>
                <CardDescription>
                  Complete challenges to earn points
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span>Completed</span>
                    <span>{completedChallenges}/{totalChallenges}</span>
                  </div>
                  <Progress 
                    value={(completedChallenges / totalChallenges) * 100} 
                    className="h-2"
                  />
                  <Badge variant="outline" className="w-full justify-center">
                    {Math.round((completedChallenges / totalChallenges) * 100)}% Complete
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Leaderboard and Challenges */}
          <div className="lg:col-span-2 space-y-6">
            {/* Leaderboard */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="w-5 h-5 text-yellow-500" />
                  Global Leaderboard
                </CardTitle>
                <CardDescription>
                  Top sustainable shoppers this month
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {leaderboard.map((user) => (
                    <div
                      key={user.id}
                      className={`flex items-center gap-4 p-3 rounded-lg transition-colors ${
                        user.name === "Manoj" 
                          ? "bg-primary/10 border border-primary/20" 
                          : "hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                          user.rank === 1 ? "bg-yellow-100 text-yellow-800" :
                          user.rank === 2 ? "bg-gray-100 text-gray-800" :
                          user.rank === 3 ? "bg-orange-100 text-orange-800" :
                          "bg-muted text-muted-foreground"
                        }`}>
                          {user.rank}
                        </div>
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center text-primary-foreground font-semibold ${
                          user.name === "Manoj" ? "bg-primary" : "bg-gradient-hero"
                        }`}>
                          {user.avatar}
                        </div>
                      </div>
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground">{user.name}</span>
                          {user.name === "Manoj" && (
                            <Badge variant="secondary" className="text-xs">You</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{user.score} pts</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Leaf className="w-3 h-3 text-green-500" />
                            {user.sustainabilityScore}% eco
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Challenges */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-blue-500" />
                  Active Challenges
                </CardTitle>
                <CardDescription>
                  Complete challenges to earn points and badges
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {challenges.map((challenge) => (
                    <div
                      key={challenge.id}
                      className={`p-4 rounded-lg border transition-colors ${
                        challenge.completed 
                          ? "bg-green-50 border-green-200" 
                          : "bg-card border-border hover:border-primary/20"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="font-medium text-foreground">{challenge.title}</h3>
                            {challenge.completed && (
                              <Badge variant="default" className="bg-green-500">
                                <Award className="w-3 h-3 mr-1" />
                                Completed
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mb-3">
                            {challenge.description}
                          </p>
                          {!challenge.completed && (
                            <div className="space-y-2">
                              <div className="flex justify-between text-sm">
                                <span>Progress</span>
                                <span>{challenge.progress}/{challenge.maxProgress}</span>
                              </div>
                              <Progress 
                                value={(challenge.progress / challenge.maxProgress) * 100} 
                                className="h-2"
                              />
                            </div>
                          )}
                        </div>
                        <div className="ml-4 text-right">
                          <div className="text-lg font-semibold text-primary">
                            +{challenge.points}
                          </div>
                          <div className="text-xs text-muted-foreground">points</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Analytics;
