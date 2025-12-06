/**
 * Compliance Check Page
 */
import { Scale, AlertTriangle, CheckCircle, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function HSCodeCompliance() {
  const complianceAreas = [
    {
      title: "Import Licenses",
      description: "Certain products require import licenses from regulatory agencies.",
      examples: ["Firearms (ATF)", "Pharmaceuticals (FDA)", "Alcohol/Tobacco (TTB)", "Wildlife (USFWS)"],
      icon: FileText,
      color: "text-blue-400",
    },
    {
      title: "Quotas",
      description: "Some products are subject to import quotas limiting the quantity.",
      examples: ["Textiles (certain countries)", "Agricultural products", "Steel/Aluminum (232)"],
      icon: Scale,
      color: "text-purple-400",
    },
    {
      title: "Sanctions",
      description: "Trade restrictions on certain countries, entities, or individuals.",
      examples: ["OFAC Sanctions", "Entity List", "Country-specific restrictions"],
      icon: AlertTriangle,
      color: "text-red-400",
    },
    {
      title: "Product Standards",
      description: "Products must meet safety and labeling requirements.",
      examples: ["CPSC (consumer products)", "DOT (transportation)", "EPA (environmental)"],
      icon: CheckCircle,
      color: "text-emerald-400",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Scale className="h-5 w-5 text-emerald-400" />
            Compliance Check
          </h1>
          <p className="text-sm text-slate-400">
            Import compliance requirements and restrictions
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {complianceAreas.map((area) => (
            <Card key={area.title} className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <area.icon className={`h-5 w-5 ${area.color}`} />
                  {area.title}
                </CardTitle>
                <CardDescription>{area.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {area.examples.map((ex, i) => (
                    <Badge key={i} variant="outline" className="border-slate-600 text-slate-300">
                      {ex}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="bg-amber-900/20 border-amber-800/50 mt-8">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-amber-400">Disclaimer</p>
              <p className="text-sm text-slate-400 mt-1">
                This information is for reference only. Always verify compliance requirements with
                official government sources and consult with a licensed customs broker for specific
                import requirements.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

