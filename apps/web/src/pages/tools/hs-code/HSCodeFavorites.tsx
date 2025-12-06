/**
 * Favorite HS Codes
 */
import { Star, Package } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function HSCodeFavorites() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Star className="h-5 w-5 text-amber-400" />
            Favorite HS Codes
          </h1>
          <p className="text-sm text-slate-400">
            Quick access to your frequently used HS codes
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="py-12 text-center">
            <Star className="h-12 w-12 mx-auto text-slate-600 mb-4" />
            <p className="text-slate-400 mb-2">No favorites yet</p>
            <p className="text-sm text-slate-500">
              Star classifications to add them to your favorites for quick access
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

