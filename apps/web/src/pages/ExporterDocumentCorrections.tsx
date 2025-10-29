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
  CheckCircle
} from "lucide-react";

const ExporterDocumentCorrections = () => {
  const [selectedIssues, setSelectedIssues] = useState<string[]>([]);
  const [correctionType, setCorrectionType] = useState<string>("");
  const [additionalComments, setAdditionalComments] = useState("");
  const [urgencyLevel, setUrgencyLevel] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Mock data for discrepancies found
  const documentIssues = [
    {
      id: "1",
      document: "Commercial Invoice",
      issue: "Invoice amount exceeds LC value by USD 1,500",
      severity: "high",
      suggestedFix: "Reduce invoice amount to match LC value of USD 50,000"
    },
    {
      id: "2", 
      document: "Bill of Lading",
      issue: "Port of loading doesn't match LC requirements",
      severity: "medium",
      suggestedFix: "Update port to 'Chittagong Port' as specified in LC"
    },
    {
      id: "3",
      document: "Certificate of Origin",
      issue: "Missing authentication stamp from Chamber of Commerce",
      severity: "high", 
      suggestedFix: "Obtain proper authentication from Bangladesh Chamber"
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
          <Link to="/exporter-results" className="inline-flex items-center text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Results
          </Link>
          <h1 className="text-3xl font-bold text-foreground">Request Document Corrections</h1>
          <p className="text-muted-foreground mt-2">
            Request corrections for identified discrepancies in your export documents
          </p>
        </div>

        {/* LC Info */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              LC Reference: EXP-BD-2024-001
            </CardTitle>
            <CardDescription>
              Bangladesh Exports Ltd → Indian Cotton Mills Ltd
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Correction Request Form */}
        <div className="grid gap-6">
          {/* Issues Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select Issues to Correct</CardTitle>
              <CardDescription>
                Choose which discrepancies you'd like to request corrections for
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
                      <p className="text-sm text-green-600">
                        <strong>Suggested Fix:</strong> {issue.suggestedFix}
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
              <CardTitle>Correction Request Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="correction-type">Type of Correction Request</Label>
                <Select value={correctionType} onValueChange={setCorrectionType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select correction type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="document-amendment">Document Amendment</SelectItem>
                    <SelectItem value="bank-notification">Bank Notification</SelectItem>
                    <SelectItem value="customs-clarification">Customs Clarification</SelectItem>
                    <SelectItem value="supplier-coordination">Supplier Coordination</SelectItem>
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
                    <SelectItem value="low">Low - Standard processing</SelectItem>
                    <SelectItem value="medium">Medium - Expedited processing</SelectItem>
                    <SelectItem value="high">High - Urgent (shipment at risk)</SelectItem>
                    <SelectItem value="critical">Critical - Immediate attention required</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="comments">Additional Comments & Instructions</Label>
                <Textarea
                  id="comments"
                  placeholder="Provide any additional context, specific instructions, or constraints for the correction request..."
                  value={additionalComments}
                  onChange={(e) => setAdditionalComments(e.target.value)}
                  rows={4}
                />
              </div>
            </CardContent>
          </Card>

          {/* Contact Information */}
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
              <CardDescription>
                Who should be contacted for this correction request?
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="contact-name">Contact Person</Label>
                  <Input id="contact-name" placeholder="Your name" />
                </div>
                <div>
                  <Label htmlFor="contact-email">Email Address</Label>
                  <Input id="contact-email" type="email" placeholder="your@email.com" />
                </div>
                <div>
                  <Label htmlFor="contact-phone">Phone Number</Label>
                  <Input id="contact-phone" placeholder="+880 XXX XXX XXXX" />
                </div>
                <div>
                  <Label htmlFor="preferred-time">Preferred Contact Time</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select time preference" />
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
            <Link to="/exporter-results">
              <Button variant="outline">
                Cancel
              </Button>
            </Link>
            <Button 
              onClick={handleSubmitRequest}
              disabled={selectedIssues.length === 0 || !correctionType || !urgencyLevel || isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Submit Request
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExporterDocumentCorrections;