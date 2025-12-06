/**
 * Bulk Upload Page
 */
import { Upload, FileSpreadsheet, Download, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function HSCodeBulk() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Upload className="h-5 w-5 text-emerald-400" />
            Bulk Classification
          </h1>
          <p className="text-sm text-slate-400">
            Classify multiple products at once using CSV upload
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Upload Products</CardTitle>
              <CardDescription>
                Upload a CSV file with product descriptions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-emerald-500 transition-colors cursor-pointer">
                <Upload className="h-10 w-10 mx-auto text-slate-500 mb-3" />
                <p className="text-slate-400">Drag and drop your CSV file here</p>
                <p className="text-sm text-slate-500 mt-1">or click to browse</p>
                <Badge variant="outline" className="mt-3 border-slate-600">
                  <FileSpreadsheet className="h-3 w-3 mr-1" />
                  CSV up to 1,000 rows
                </Badge>
              </div>

              <Button className="w-full bg-emerald-600" disabled>
                <Upload className="h-4 w-4 mr-2" />
                Process File
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-base">Template Format</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-mono text-xs bg-slate-900 p-3 rounded">
                  <p className="text-slate-500"># CSV columns:</p>
                  <p className="text-emerald-400">description, import_country, export_country</p>
                  <p className="text-slate-400 mt-2">"Cotton t-shirts",US,CN</p>
                  <p className="text-slate-400">"Laptop computers",US,TW</p>
                  <p className="text-slate-400">"Roasted coffee beans",US,CO</p>
                </div>
                <Button variant="outline" size="sm" className="mt-3">
                  <Download className="h-4 w-4 mr-2" />
                  Download Template
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-blue-900/20 border-blue-800/50">
              <CardContent className="p-4 flex items-start gap-3">
                <Info className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-slate-400">
                  <p className="font-medium text-blue-400 mb-1">Pro Feature</p>
                  <p>Bulk classification is available on Pro plans. Results include confidence scores, duty rates, and FTA eligibility for each product.</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

