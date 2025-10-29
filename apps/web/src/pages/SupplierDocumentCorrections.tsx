import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { 
  ArrowLeft, 
  Send, 
  FileText, 
  AlertTriangle, 
  Clock, 
  XCircle,
  TrendingUp
} from "lucide-react";

const SupplierDocumentCorrections = () => {
  const [selectedIssues, setSelectedIssues] = useState<string[]>([]);
  const [correctionMethod, setCorrectionMethod] = useState<string>("");
  const [additionalComments, setAdditionalComments] = useState("");
  const [urgencyLevel, setUrgencyLevel] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mock data for supplier document issues
  const documentIssues = [
    {
      id: "1",
      document: "Commercial Invoice",
      issue: "Invoice amount USD 51,500 exceeds LC value USD 50,000",
      severity: "high",
      currentValue: "USD 51,500",
      lcValue: "USD 50,000",
      suggestedFix: "Supplier must issue revised invoice with correct amount USD 50,000"
    },
    {
      id: "2", 
      document: "Bill of Lading",
      issue: "Port of loading shows 'Mumbai' but LC requires 'JNPT Port'",
      severity: "high",
      currentValue: "Mumbai",
      lcValue: "JNPT Port",
      suggestedFix: "Shipping line must reissue B/L with correct port of loading"
    },
    {
      id: "3",
      document: "Certificate of Origin",
      issue: "Missing Chamber of Commerce authentication stamp",
      severity: "medium", 
      currentValue: "No authentication visible",
      lcValue: "Must be authenticated by Chamber",
      suggestedFix: "Supplier must get COO authenticated by Indian Chamber of Commerce"
    },
    {
      id: "4",
      document: "Packing List",
      issue: "Package count shows 95 bales but invoice shows 100 bales",
      severity: "medium",
      currentValue: "95 bales",
      lcValue: "Should match invoice: 100 bales",
      suggestedFix: "Supplier must reconcile and correct package count"
    }
  ];

  const handleIssueToggle = (issueId: string) => {
    setSelectedIssues(prev => 
      prev.includes(issueId) 
        ? prev.filter(id => id !== issueId)
        : [...prev, issueId]
    );
  };

  const handleSubmitRequest = () => {
    setIsSubmitting(true);
    // Simulate API call
    setTimeout(() => {
      setIsSubmitting(false);
      // Navigate to success page or show toast
    }, 2000);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high": return "destructive";
      case "medium": return "secondary";
      default: return "default";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <Link to="/supplier-document-results" className="inline-flex items-center text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Compliance Results
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Request Supplier Document Corrections</h1>
          <p className="text-muted-foreground mt-2">
            Request corrections from your supplier for document discrepancies
          </p>
        </div>

        {/* LC Info */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              LC Reference: IMP-BD-2024-001
            </CardTitle>
            <CardDescription>
              Bangladesh Textiles Ltd ← Indian Cotton Mills Ltd
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Correction Request Form */}
        <div className="grid gap-6">
          {/* Issues Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select Document Issues to Correct</CardTitle>
              <CardDescription>
                Choose which discrepancies you'd like your supplier to fix
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {documentIssues.map((issue) => (
                <div key={issue.id} className="border rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <Checkbox 
                      id={issue.id}
                      checked={selectedIssues.includes(issue.id)}
                      onCheckedChange={() => handleIssueToggle(issue.id)}
                    />
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <Label htmlFor={issue.id} className="font-medium">
                          {issue.document}
                        </Label>
                        <Badge variant={getSeverityColor(issue.severity) as any}>
                          {issue.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        <strong>Issue:</strong> {issue.issue}
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                        <p className="text-red-600">
                          <strong>Current:</strong> {issue.currentValue}
                        </p>
                        <p className="text-green-600">
                          <strong>Required:</strong> {issue.lcValue}
                        </p>
                      </div>
                      <p className="text-sm text-blue-600">
                        <strong>Action Required:</strong> {issue.suggestedFix}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Request Details */}
          <Card>
            <CardHeader>
              <CardTitle>Correction Request Method</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="correction-method">How to contact supplier?</Label>
                <Select value={correctionMethod} onValueChange={setCorrectionMethod}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select correction method" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email-formal">Formal Email with Detailed Report</SelectItem>
                    <SelectItem value="email-urgent">Urgent Email with Phone Follow-up</SelectItem>
                    <SelectItem value="whatsapp">WhatsApp/Phone Call (Immediate)</SelectItem>
                    <SelectItem value="agent">Through Local Agent/Representative</SelectItem>
                    <SelectItem value="bank">Through Bank Notification</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="urgency">Urgency Level</Label>
                <Select value={urgencyLevel} onValueChange={setUrgencyLevel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select urgency level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low - Standard processing time</SelectItem>
                    <SelectItem value="medium">Medium - Need response within 2 days</SelectItem>
                    <SelectItem value="high">High - Ship arrival imminent</SelectItem>
                    <SelectItem value="critical">Critical - Demurrage charges at risk</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="comments">Message to Supplier</Label>
                <Textarea
                  id="comments"
                  placeholder="Dear Supplier,&#10;&#10;We have reviewed the documents you provided for LC IMP-BD-2024-001 and found some discrepancies that need immediate correction to avoid customs delays...&#10;&#10;Please provide corrected documents urgently."
                  value={additionalComments}
                  onChange={(e) => setAdditionalComments(e.target.value)}
                  rows={6}
                />
              </div>
            </CardContent>
          </Card>

          {/* Supplier Contact Information */}
          <Card>
            <CardHeader>
              <CardTitle>Supplier Contact Details</CardTitle>
              <CardDescription>
                Confirm supplier contact information for correction request
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="supplier-name">Supplier Name</Label>
                  <Input id="supplier-name" placeholder="Indian Cotton Mills Ltd" />
                </div>
                <div>
                  <Label htmlFor="supplier-contact">Supplier Contact Person</Label>
                  <Input id="supplier-contact" placeholder="Mr. Raj Kumar (Export Manager)" />
                </div>
                <div>
                  <Label htmlFor="supplier-email">Supplier Email</Label>
                  <Input id="supplier-email" type="email" placeholder="export@indiancotton.com" />
                </div>
                <div>
                  <Label htmlFor="supplier-phone">Supplier Phone/WhatsApp</Label>
                  <Input id="supplier-phone" placeholder="+91 XXX XXX XXXX" />
                </div>
                <div>
                  <Label htmlFor="cc-email">CC Additional Emails</Label>
                  <Input id="cc-email" placeholder="manager@indiancotton.com" />
                </div>
                <div>
                  <Label htmlFor="deadline">Response Deadline</Label>
                  <Input id="deadline" type="date" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Consequences Warning */}
          <Card className="border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-yellow-800 dark:text-yellow-200">
                <AlertTriangle className="h-5 w-5" />
                Important Notice
              </CardTitle>
            </CardHeader>
            <CardContent className="text-yellow-700 dark:text-yellow-300">
              <p className="text-sm">
                Uncorrected document discrepancies may result in:
              </p>
              <ul className="text-sm mt-2 space-y-1 list-disc list-inside">
                <li>Customs clearance delays</li>
                <li>Demurrage and storage charges</li>
                <li>Bank discrepancy fees</li>
                <li>Potential shipment rejection</li>
              </ul>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-4 justify-end">
            <Link to="/supplier-document-results">
              <Button variant="outline">
                Cancel
              </Button>
            </Link>
            <Button 
              onClick={handleSubmitRequest}
              disabled={selectedIssues.length === 0 || !correctionMethod || !urgencyLevel || isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
                  Sending Request...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Correction Request
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupplierDocumentCorrections;