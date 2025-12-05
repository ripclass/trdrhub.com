/**
 * MT700 Reference Page
 * 
 * Complete guide to SWIFT MT700 message fields for LC applications.
 */

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Search,
  FileCheck,
  Info,
  AlertTriangle,
} from "lucide-react";

interface MT700Field {
  tag: string;
  name: string;
  status: "mandatory" | "optional" | "conditional";
  description: string;
  format: string;
  example: string;
  notes?: string;
}

const mt700Fields: MT700Field[] = [
  {
    tag: "27",
    name: "Sequence of Total",
    status: "mandatory",
    description: "Indicates sequence number in multi-message LC",
    format: "1!n/1!n",
    example: "1/1",
    notes: "Use 1/1 for single message LC",
  },
  {
    tag: "40A",
    name: "Form of Documentary Credit",
    status: "mandatory",
    description: "Type of documentary credit",
    format: "24x",
    example: "IRREVOCABLE",
    notes: "Values: IRREVOCABLE, IRREVOCABLE TRANSFERABLE, IRREV TRANS STANDBY",
  },
  {
    tag: "20",
    name: "Documentary Credit Number",
    status: "mandatory",
    description: "Unique reference assigned by issuing bank",
    format: "16x",
    example: "LC2024000123",
    notes: "Must be unique. Used for all future references.",
  },
  {
    tag: "23",
    name: "Reference to Pre-Advice",
    status: "optional",
    description: "Reference to preliminary advice",
    format: "16x",
    example: "PREADVICE001",
  },
  {
    tag: "31C",
    name: "Date of Issue",
    status: "mandatory",
    description: "Date LC was issued",
    format: "6!n (YYMMDD)",
    example: "241205",
    notes: "Format: YYMMDD",
  },
  {
    tag: "40E",
    name: "Applicable Rules",
    status: "mandatory",
    description: "Rules governing the LC",
    format: "30x",
    example: "UCP LATEST VERSION",
    notes: "Usually UCP LATEST VERSION or EUCP LATEST VERSION",
  },
  {
    tag: "31D",
    name: "Date and Place of Expiry",
    status: "mandatory",
    description: "When and where LC expires",
    format: "6!n29x",
    example: "250305BANGLADESH",
    notes: "Date (YYMMDD) + Place name",
  },
  {
    tag: "50",
    name: "Applicant",
    status: "mandatory",
    description: "Name and address of applicant (buyer)",
    format: "4*35x",
    example: "ABC TRADING CO LTD\n123 COMMERCE ST\nNEW YORK NY 10001\nUSA",
    notes: "Up to 4 lines, 35 characters each",
  },
  {
    tag: "59",
    name: "Beneficiary",
    status: "mandatory",
    description: "Name and address of beneficiary (seller)",
    format: "[/34x]4*35x",
    example: "FASHION GARMENTS LTD\nPLOT 123 BSCIC\nDHAKA\nBANGLADESH",
    notes: "Account number optional, then 4 lines name/address",
  },
  {
    tag: "32B",
    name: "Currency Code, Amount",
    status: "mandatory",
    description: "LC currency and amount",
    format: "3!a15d",
    example: "USD100000,00",
    notes: "ISO currency code + amount (comma for decimals)",
  },
  {
    tag: "39A",
    name: "Percentage Credit Amount Tolerance",
    status: "optional",
    description: "Tolerance for credit amount",
    format: "2n/2n",
    example: "05/05",
    notes: "+/- percentage tolerance (e.g., 05/05 = +/-5%)",
  },
  {
    tag: "39B",
    name: "Maximum Credit Amount",
    status: "conditional",
    description: "Credit amount not to exceed indicator",
    format: "13x",
    example: "NOT EXCEEDING",
  },
  {
    tag: "39C",
    name: "Additional Amounts Covered",
    status: "optional",
    description: "Additional amounts (insurance, freight)",
    format: "4*35x",
    example: "INSURANCE AND FREIGHT",
  },
  {
    tag: "41A/D",
    name: "Available With...By...",
    status: "mandatory",
    description: "Bank where LC is available and how",
    format: "4!a2!a2!c[3!c] + 14x",
    example: "SCBLBDDX\nBY NEGOTIATION",
    notes: "Bank BIC + availability type (BY PAYMENT, BY ACCEPTANCE, BY NEGOTIATION, BY DEF PAYMENT)",
  },
  {
    tag: "42C",
    name: "Drafts at...",
    status: "conditional",
    description: "Draft tenor",
    format: "3*35x",
    example: "SIGHT",
    notes: "Required if payment is by acceptance or negotiation of draft",
  },
  {
    tag: "42A/D",
    name: "Drawee",
    status: "conditional",
    description: "Bank on which drafts are drawn",
    format: "4!a2!a2!c[3!c]",
    example: "CITIUS33",
    notes: "Required if drafts are required",
  },
  {
    tag: "43P",
    name: "Partial Shipments",
    status: "optional",
    description: "Whether partial shipments allowed",
    format: "11x",
    example: "ALLOWED",
    notes: "ALLOWED or NOT ALLOWED. Default is allowed if not stated.",
  },
  {
    tag: "43T",
    name: "Transhipment",
    status: "optional",
    description: "Whether transhipment allowed",
    format: "11x",
    example: "ALLOWED",
    notes: "ALLOWED or NOT ALLOWED. Default is allowed if not stated.",
  },
  {
    tag: "44E",
    name: "Port of Loading/Airport of Departure",
    status: "conditional",
    description: "Place where goods are loaded",
    format: "65x",
    example: "CHITTAGONG PORT, BANGLADESH",
  },
  {
    tag: "44F",
    name: "Port of Discharge/Airport of Destination",
    status: "conditional",
    description: "Place where goods are discharged",
    format: "65x",
    example: "NEW YORK, USA",
  },
  {
    tag: "44B",
    name: "Place of Final Destination/For Transportation to.../Place of Delivery",
    status: "optional",
    description: "Final destination of goods",
    format: "65x",
    example: "NEW YORK WAREHOUSE, USA",
  },
  {
    tag: "44C",
    name: "Latest Date of Shipment",
    status: "conditional",
    description: "Last date for shipment",
    format: "6!n",
    example: "250215",
    notes: "Format: YYMMDD",
  },
  {
    tag: "44D",
    name: "Shipment Period",
    status: "conditional",
    description: "Period during which shipment must occur",
    format: "6*65x",
    example: "SHIPMENT DURING JANUARY 2025",
    notes: "Alternative to field 44C",
  },
  {
    tag: "45A",
    name: "Description of Goods and/or Services",
    status: "mandatory",
    description: "Detailed description of goods",
    format: "100*65x",
    example: "100% COTTON WOVEN SHIRTS\nSTYLE: CASUAL\nCOMPOSITION: 100% COTTON\nQUANTITY: 10,000 PCS",
    notes: "Must match exactly on invoice. Other docs can use general terms.",
  },
  {
    tag: "46A",
    name: "Documents Required",
    status: "mandatory",
    description: "List of required documents",
    format: "100*65x",
    example: "+SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS\n+FULL SET 3/3 ORIGINAL CLEAN ON BOARD B/L\n+PACKING LIST IN 2 COPIES",
    notes: "Each document typically starts with + symbol",
  },
  {
    tag: "47A",
    name: "Additional Conditions",
    status: "optional",
    description: "Additional terms and conditions",
    format: "100*65x",
    example: "+ALL DOCUMENTS MUST QUOTE LC NUMBER\n+THIRD PARTY DOCUMENTS ACCEPTABLE",
  },
  {
    tag: "71D",
    name: "Charges",
    status: "optional",
    description: "Banking charges allocation",
    format: "6*35x",
    example: "ALL BANKING CHARGES OUTSIDE BANGLADESH FOR ACCOUNT OF APPLICANT",
  },
  {
    tag: "48",
    name: "Period for Presentation in Days",
    status: "mandatory",
    description: "Days after shipment to present documents",
    format: "3n/35x",
    example: "21",
    notes: "Default is 21 days per UCP600",
  },
  {
    tag: "49",
    name: "Confirmation Instructions",
    status: "mandatory",
    description: "Whether confirmation is requested",
    format: "7x",
    example: "WITHOUT",
    notes: "CONFIRM, MAY ADD, or WITHOUT",
  },
  {
    tag: "53A/D",
    name: "Reimbursing Bank",
    status: "optional",
    description: "Bank providing reimbursement",
    format: "4!a2!a2!c[3!c]",
    example: "CITIUS33",
  },
  {
    tag: "78",
    name: "Instructions to Paying/Accepting/Negotiating Bank",
    status: "optional",
    description: "Special instructions for nominated bank",
    format: "12*65x",
    example: "UPON RECEIPT OF DOCUMENTS IN COMPLIANCE\nPLEASE CLAIM REIMBURSEMENT FROM\nCITIBANK NEW YORK",
  },
  {
    tag: "57A/D",
    name: "Advise Through Bank",
    status: "conditional",
    description: "Bank through which LC is advised",
    format: "4!a2!a2!c[3!c]",
    example: "SCBLBDDX",
    notes: "Required if different from available with bank",
  },
  {
    tag: "72Z",
    name: "Sender to Receiver Information",
    status: "optional",
    description: "Additional information for receiver",
    format: "6*35x",
    example: "PLEASE ADVISE BENEFICIARY URGENTLY",
  },
];

const statusColors: Record<string, string> = {
  mandatory: "bg-red-500/10 text-red-400",
  optional: "bg-green-500/10 text-green-400",
  conditional: "bg-yellow-500/10 text-yellow-400",
};

export default function MT700ReferencePage() {
  const [searchQuery, setSearchQuery] = useState("");
  
  const filteredFields = mt700Fields.filter((field) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      field.tag.toLowerCase().includes(query) ||
      field.name.toLowerCase().includes(query) ||
      field.description.toLowerCase().includes(query)
    );
  });

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-emerald-400" />
              MT700 Reference Guide
            </h1>
            <p className="text-sm text-slate-400">
              Complete guide to SWIFT MT700 documentary credit message fields
            </p>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="px-6 py-4 border-b border-slate-800">
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-400 mt-0.5" />
            <div>
              <h3 className="font-medium text-blue-400">About SWIFT MT700</h3>
              <p className="text-sm text-slate-300 mt-1">
                MT700 is the SWIFT message type used by banks to issue documentary credits. 
                Understanding these fields helps you create LC applications that banks can process efficiently.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-6 py-4 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search by field tag or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-slate-800 border-slate-700"
            />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Badge className={statusColors.mandatory}>Mandatory</Badge>
            <Badge className={statusColors.optional}>Optional</Badge>
            <Badge className={statusColors.conditional}>Conditional</Badge>
          </div>
        </div>
      </div>

      {/* Fields List */}
      <div className="px-6 py-6">
        <Accordion type="multiple" className="space-y-2">
          {filteredFields.map((field) => (
            <AccordionItem
              key={field.tag}
              value={field.tag}
              className="border border-slate-700 rounded-lg bg-slate-800/30"
            >
              <AccordionTrigger className="px-4 hover:no-underline">
                <div className="flex items-center gap-4 w-full">
                  <Badge variant="outline" className="font-mono">
                    {field.tag}
                  </Badge>
                  <span className="font-medium text-white flex-1 text-left">
                    {field.name}
                  </span>
                  <Badge className={statusColors[field.status]}>
                    {field.status}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4">
                <div className="space-y-4">
                  <p className="text-slate-300">{field.description}</p>
                  
                  <div className="grid gap-4 md:grid-cols-2">
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-slate-400">Format</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <code className="text-emerald-400 font-mono text-sm">
                          {field.format}
                        </code>
                      </CardContent>
                    </Card>
                    
                    <Card className="bg-slate-800/50 border-slate-700">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-slate-400">Example</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <pre className="text-white font-mono text-sm whitespace-pre-wrap">
                          {field.example}
                        </pre>
                      </CardContent>
                    </Card>
                  </div>
                  
                  {field.notes && (
                    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-400 mt-0.5" />
                        <p className="text-sm text-slate-300">{field.notes}</p>
                      </div>
                    </div>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
        
        {filteredFields.length === 0 && (
          <div className="text-center py-12">
            <Search className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No fields found</h3>
            <p className="text-slate-400">Try a different search term</p>
          </div>
        )}
      </div>
    </div>
  );
}

