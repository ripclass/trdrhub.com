/**
 * Rules of Origin Reference
 */
import { FileCheck, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function HSCodeROO() {
  const rooTypes = [
    {
      type: "CTC - Change in Tariff Classification",
      description: "Product must undergo a change in tariff classification at the chapter (CC), heading (CTH), or subheading (CTSH) level.",
      examples: ["CC: Change from any other chapter", "CTH: Change from any other heading", "CTSH: Change from any other subheading"],
    },
    {
      type: "RVC - Regional Value Content",
      description: "A minimum percentage of the product's value must originate from FTA member countries.",
      examples: ["Build-down: (AV - VNM) / AV × 100", "Build-up: VOM / AV × 100", "Net cost: (NC - VNM) / NC × 100"],
    },
    {
      type: "SP - Specific Process",
      description: "Product must undergo specific manufacturing processes within the FTA territory.",
      examples: ["Chemical reaction", "Purification", "Assembly operations"],
    },
  ];

  const cumulation = [
    { type: "Bilateral", description: "Materials from two partner countries can be combined." },
    { type: "Diagonal", description: "Materials from any FTA member can be used without affecting origin." },
    { type: "Full", description: "Any processing in member countries contributes to origin requirements." },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-emerald-400" />
            Rules of Origin Reference
          </h1>
          <p className="text-sm text-slate-400">
            Understanding origin requirements for preferential trade
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8 space-y-8">
        {/* ROO Types */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Types of Origin Rules</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {rooTypes.map((rule) => (
              <Card key={rule.type} className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-base">{rule.type.split(" - ")[0]}</CardTitle>
                  <CardDescription>{rule.type.split(" - ")[1]}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-400 mb-3">{rule.description}</p>
                  <div className="space-y-1">
                    {rule.examples.map((ex, i) => (
                      <div key={i} className="text-xs text-slate-500 font-mono bg-slate-900 px-2 py-1 rounded">
                        {ex}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Cumulation */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Cumulation Types</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {cumulation.map((c) => (
              <Card key={c.type} className="bg-slate-800 border-slate-700">
                <CardContent className="p-4">
                  <Badge className="bg-purple-500/20 text-purple-400 mb-2">{c.type}</Badge>
                  <p className="text-sm text-slate-400">{c.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* De Minimis */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-400" />
              De Minimis Rule
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-400 mb-4">
              The de minimis rule allows a small percentage of non-originating materials without
              disqualifying the product from preferential treatment.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 bg-slate-900 rounded-lg text-center">
                <p className="text-xs text-slate-500">USMCA</p>
                <p className="text-lg font-bold text-white">10%</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg text-center">
                <p className="text-xs text-slate-500">RCEP</p>
                <p className="text-lg font-bold text-white">10%</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg text-center">
                <p className="text-xs text-slate-500">CPTPP</p>
                <p className="text-lg font-bold text-white">10%</p>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg text-center">
                <p className="text-xs text-slate-500">GSP</p>
                <p className="text-lg font-bold text-white">35%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

