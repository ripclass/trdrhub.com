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
  ShieldCheck,
  AlertCircle
} from "lucide-react";

const DraftLCCorrections = () => {
  const [selectedRisks, setSelectedRisks] = useState<string[]>([]);
  const [requestType, setRequestType] = useState<string>("");
  const [additionalComments, setAdditionalComments] = useState("");
  const [urgencyLevel, setUrgencyLevel] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mock data for LC risk clauses
  const riskClauses = [
    {
      id: "1",
      type: "Shipment Terms",
      clause: "Latest shipment date: 15 days from LC opening date",
      riskLevel: "high",
      issue: "Very tight timeline may cause supplier delays",
      suggestedAmendment: "Extend to 30 days minimum for international shipments"
    },
    {
      id: "2", 
      type: "Document Requirements",
      clause: "Certificate of Origin must be issued by Delhi Chamber of Commerce",
      riskLevel: "medium",
      issue: "Specific chamber requirement may limit supplier flexibility",
      suggestedAmendment: "Accept COO from any recognized Indian Chamber of Commerce"
    },
    {
      id: "3",
      type: "Payment Terms", 
      clause: "Documents must be presented within 7 days of shipment",
      riskLevel: "high",
      issue: "Short presentation period increases risk of late fees",
      suggestedAmendment: "Extend to 21 days as per UCP 600 standard"
    },
    {
      id: "4",
      type: "Goods Description",
      clause: "Cotton Raw Material, Grade A, moisture content max 8%",
      riskLevel: "medium", 
      issue: "Very specific quality parameters may cause rejection",
      suggestedAmendment: "Add tolerance clause: ± 0.5% moisture content acceptable"
    }
  ];

  const handleRiskToggle = (riskId: string) => {
    setSelectedRisks(prev => 
      prev.includes(riskId) 
        ? prev.filter(id => id !== riskId)
        : [...prev, riskId]
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

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case "high": return "destructive";
      case "medium": return "secondary";
      default: return "default";
    }
  };

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case "high": return <AlertTriangle className="h-4 w-4" />;
      case "medium": return <AlertCircle className="h-4 w-4" />;
      default: return <ShieldCheck className="h-4 w-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <Link to="/draft-lc-risk-results" className="inline-flex items-center text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Risk Analysis
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Request LC Amendment</h1>
          <p className="text-muted-foreground mt-2">
            Request amendments to reduce risks in your draft Letter of Credit
          </p>
        </div>

        {/* LC Info */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Draft LC: DRAFT-LC-BD-2024-001
            </CardTitle>
            <CardDescription>
              Bangladesh Textiles Ltd ← Indian Cotton Mills Ltd
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Risk Amendment Form */}
        <div className="grid gap-6">
          {/* Risk Clauses Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select Risk Clauses to Amend</CardTitle>
              <CardDescription>
                Choose which risky clauses you'd like to request amendments for
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {riskClauses.map((risk) => (
                <div key={risk.id} className="border rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <Checkbox 
                      id={risk.id}
                      checked={selectedRisks.includes(risk.id)}
                      onCheckedChange={() => handleRiskToggle(risk.id)}
                    />
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <Label htmlFor={risk.id} className="font-medium">
                          {risk.type}
                        </Label>
                        <Badge variant={getRiskColor(risk.riskLevel) as any} className="flex items-center gap-1">
                          {getRiskIcon(risk.riskLevel)}
                          {risk.riskLevel} risk
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        <strong>Current Clause:</strong> {risk.clause}
                      </p>
                      <p className="text-sm text-red-600">
                        <strong>Risk:</strong> {risk.issue}
                      </p>
                      <p className="text-sm text-green-600">
                        <strong>Suggested Amendment:</strong> {risk.suggestedAmendment}
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
              <CardTitle>Amendment Request Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="request-type">Type of Request</Label>
                <Select value={requestType} onValueChange={setRequestType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select request type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank-amendment">Request Bank to Amend LC</SelectItem>
                    <SelectItem value="supplier-negotiation">Negotiate with Supplier</SelectItem>
                    <SelectItem value="both">Both Bank Amendment & Supplier Discussion</SelectItem>
                    <SelectItem value="risk-acceptance">Accept Risk with Mitigation Plan</SelectItem>
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
                    <SelectItem value="low">Low - Review before LC opening</SelectItem>
                    <SelectItem value="medium">Medium - Needs resolution soon</SelectItem>
                    <SelectItem value="high">High - LC opening delayed</SelectItem>
                    <SelectItem value="critical">Critical - Shipment timeline at risk</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="comments">Additional Context & Constraints</Label>
                <Textarea
                  id="comments"
                  placeholder="Provide any business context, supplier relationships, or specific constraints that should be considered for these amendments..."
                  value={additionalComments}
                  onChange={(e) => setAdditionalComments(e.target.value)}
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          {/* Bank Contact Information */}
          <Card>
            <CardHeader>
              <CardTitle>Bank & Contact Details</CardTitle>
              <CardDescription>
                Ensure your bank can reach you for amendment discussions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="bank-name">Issuing Bank</Label>
                  <Input id="bank-name" placeholder="e.g., BRAC Bank Limited" />
                </div>
                <div>
                  <Label htmlFor="bank-officer">Bank Officer Name</Label>
                  <Input id="bank-officer" placeholder="Your relationship manager" />
                </div>
                <div>
                  <Label htmlFor="contact-name">Your Name</Label>
                  <Input id="contact-name" placeholder="Primary contact person" />
                </div>
                <div>
                  <Label htmlFor="contact-email">Email Address</Label>
                  <Input id="contact-email" type="email" placeholder="your@company.com" />
                </div>
                <div>
                  <Label htmlFor="contact-phone">Phone Number</Label>
                  <Input id="contact-phone" placeholder="+880 XXX XXX XXXX" />
                </div>
                <div>
                  <Label htmlFor="preferred-time">Preferred Contact Time</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Best time to reach you" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="morning">Morning (9 AM - 12 PM)</SelectItem>
                      <SelectItem value="afternoon">Afternoon (12 PM - 5 PM)</SelectItem>
                      <SelectItem value="evening">Evening (5 PM - 8 PM)</SelectItem>
                      <SelectItem value="anytime">Anytime</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex gap-4 justify-end">
            <Link to="/draft-lc-risk-results">
              <Button variant="outline">
                Cancel
              </Button>
            </Link>
            <Button 
              onClick={handleSubmitRequest}
              disabled={selectedRisks.length === 0 || !requestType || !urgencyLevel || isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Submit Amendment Request
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DraftLCCorrections;