import { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ChevronDown,
  ChevronUp,
  FileText,
  CheckCircle,
  AlertTriangle,
  Download,
  HelpCircle,
  Ship,
  FileCheck,
  Shield,
  Package,
  Globe,
  Info,
  Lightbulb,
  BookOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
type ChecklistItem = {
  id: string;
  text: string;
  critical?: boolean;
  tip?: string;
};

type DocumentChecklist = {
  id: string;
  name: string;
  emoji: string;
  items: ChecklistItem[];
};

type CountryRequirements = {
  code: string;
  name: string;
  flag: string;
  requirements: ChecklistItem[];
};

// Storage key for localStorage
const STORAGE_KEY = 'lcopilot_preparation_checklist';

// Checklist Data
const PRE_UPLOAD_CHECKS: ChecklistItem[] = [
  { id: 'read-lc', text: 'Read your LC carefully - note ALL requirements in field 47A', critical: true },
  { id: 'check-expiry', text: 'Check LC expiry date - ensure you have time to fix issues' },
  { id: 'identify-docs', text: 'Identify required documents - LC field 46A lists them', critical: true },
  { id: 'note-conditions', text: 'Note any special conditions - BIN/TIN/PO requirements' },
  { id: 'check-amounts', text: 'Verify amounts match across all documents', critical: true },
];

const DOCUMENT_CHECKLISTS: DocumentChecklist[] = [
  {
    id: 'invoice',
    name: 'Commercial Invoice',
    emoji: '📄',
    items: [
      { id: 'inv-issuer', text: 'Issued by beneficiary (your company)', critical: true },
      { id: 'inv-addressee', text: 'Addressed to applicant (buyer) - exact name from LC', critical: true },
      { id: 'inv-goods', text: 'Goods description matches LC EXACTLY (copy-paste if needed)', critical: true, tip: 'Even small spelling differences can cause rejection' },
      { id: 'inv-amount', text: 'Amount matches LC (or within tolerance if specified)', critical: true },
      { id: 'inv-currency', text: 'Currency matches LC' },
      { id: 'inv-date', text: 'Invoice date is AFTER LC issue date' },
      { id: 'inv-bintin', text: 'Exporter BIN/TIN included (if required by LC 47A)' },
      { id: 'inv-signed', text: 'Signed and stamped' },
    ],
  },
  {
    id: 'packing-list',
    name: 'Packing List',
    emoji: '📦',
    items: [
      { id: 'pl-match', text: 'Matches invoice quantities exactly', critical: true },
      { id: 'pl-cartons', text: 'Shows carton/package breakdown' },
      { id: 'pl-weights', text: 'Includes gross/net weights' },
      { id: 'pl-sizes', text: 'Size breakdown (if garments - per LC requirements)' },
      { id: 'pl-bintin', text: 'BIN/TIN included (if required)' },
    ],
  },
  {
    id: 'bill-of-lading',
    name: 'Bill of Lading',
    emoji: '🚢',
    items: [
      { id: 'bl-onboard', text: '"Shipped on Board" notation with date', critical: true },
      { id: 'bl-date', text: 'Shipped on board date is BEFORE LC latest shipment date', critical: true },
      { id: 'bl-loading', text: 'Port of loading matches LC', critical: true },
      { id: 'bl-discharge', text: 'Port of discharge matches LC', critical: true },
      { id: 'bl-consignee', text: 'Consignee as per LC (usually "To Order" or bank name)' },
      { id: 'bl-notify', text: 'Notify party as per LC' },
      { id: 'bl-freight', text: 'Freight: Prepaid or Collect as per LC terms' },
      { id: 'bl-clean', text: '"Clean" - no clauses indicating damaged goods', critical: true },
      { id: 'bl-signed', text: 'Signed by carrier or agent' },
      { id: 'bl-bintin', text: 'BIN/TIN in description (if required)' },
      { id: 'bl-voyage', text: 'Voyage number and vessel name included' },
    ],
  },
  {
    id: 'certificate-of-origin',
    name: 'Certificate of Origin',
    emoji: '📜',
    items: [
      { id: 'coo-issuer', text: 'Issued by Chamber of Commerce (or as specified in LC)', critical: true },
      { id: 'coo-origin', text: 'Shows country of origin matching LC requirement' },
      { id: 'coo-goods', text: 'Goods description consistent with invoice' },
      { id: 'coo-signed', text: 'Properly signed and stamped' },
    ],
  },
  {
    id: 'insurance',
    name: 'Insurance Certificate',
    emoji: '🛡️',
    items: [
      { id: 'ins-coverage', text: 'Coverage amount = 110% of invoice value (standard)', critical: true },
      { id: 'ins-risks', text: 'Covers risks specified in LC (usually "All Risks")' },
      { id: 'ins-date', text: 'Dated BEFORE or SAME as B/L date', critical: true },
      { id: 'ins-currency', text: 'In same currency as LC' },
      { id: 'ins-endorsed', text: 'Endorsed in blank (if negotiable)' },
    ],
  },
  {
    id: 'inspection',
    name: 'Inspection Certificate',
    emoji: '🔍',
    items: [
      { id: 'insp-agency', text: 'Issued by specified agency (SGS, Intertek, etc.)', critical: true },
      { id: 'insp-date', text: 'Dated BEFORE B/L date (goods inspected pre-shipment)' },
      { id: 'insp-confirms', text: 'Confirms quality, quantity, packing as per LC' },
    ],
  },
  {
    id: 'beneficiary-cert',
    name: 'Beneficiary Certificate',
    emoji: '📝',
    items: [
      { id: 'bc-letterhead', text: 'On your company letterhead' },
      { id: 'bc-language', text: 'States EXACTLY what LC requires (copy LC language)', critical: true },
      { id: 'bc-signed', text: 'Signed by authorized signatory' },
      { id: 'bc-dated', text: 'Dated appropriately' },
    ],
  },
];

const COMMON_MISTAKES: ChecklistItem[] = [
  { id: 'err-spelling', text: 'Spelling differences - "Dhaka" vs "Dacca" = discrepancy', critical: true },
  { id: 'err-dates', text: 'Date inconsistencies - Insurance dated after B/L' },
  { id: 'err-amounts', text: 'Amount rounding - $99,999.50 vs $100,000 without tolerance' },
  { id: 'err-bintin', text: 'Missing BIN/TIN - Most common BD LC rejection reason', critical: true },
  { id: 'err-drafts', text: '"Draft" watermarks - Submit final versions only' },
  { id: 'err-unsigned', text: 'Unsigned documents - Everything must be signed' },
  { id: 'err-quality', text: 'Poor scan quality - Illegible = discrepancy' },
];

const UPLOAD_TIPS: ChecklistItem[] = [
  { id: 'tip-pdf', text: 'PDF format preferred (better OCR accuracy)' },
  { id: 'tip-dpi', text: 'Scan at 300 DPI minimum' },
  { id: 'tip-legible', text: 'Ensure all text is legible' },
  { id: 'tip-lc-first', text: 'Upload LC document first (helps system extract requirements)' },
  { id: 'tip-naming', text: 'Name files clearly: "Commercial_Invoice.pdf" not "scan001.pdf"' },
];

const COUNTRY_REQUIREMENTS: CountryRequirements[] = [
  {
    code: 'bd',
    name: 'Bangladesh',
    flag: '🇧🇩',
    requirements: [
      { id: 'bd-bin', text: 'Exporter BIN (Business Identification Number) - 11 digits', critical: true, tip: 'Format: XXX-XXXX-XXX. Must appear on: Invoice, B/L, Packing List' },
      { id: 'bd-tin', text: 'Exporter TIN (Tax Identification Number) - 12 digits', critical: true, tip: 'Format: XXXXXXXXXXXX. Must appear on: Invoice, Certificate of Origin' },
      { id: 'bd-hs', text: 'HS Code - Required on Invoice and Packing List' },
      { id: 'bd-origin', text: 'Country of Origin - Must be clearly stated' },
    ],
  },
  {
    code: 'sa',
    name: 'Saudi Arabia',
    flag: '🇸🇦',
    requirements: [
      { id: 'sa-saber', text: 'SABER Certificate may be required for certain goods', critical: true },
      { id: 'sa-coo', text: 'Certificate of Origin must be Chamber-certified' },
      { id: 'sa-arabic', text: 'Arabic translation may be required for some documents' },
      { id: 'sa-halal', text: 'Halal certificate for food products', tip: 'Must be issued by approved certification body' },
    ],
  },
  {
    code: 'ae',
    name: 'UAE',
    flag: '🇦🇪',
    requirements: [
      { id: 'ae-coo', text: 'Certificate of Origin - legalized by Chamber of Commerce' },
      { id: 'ae-conformity', text: 'Certificate of Conformity for regulated products' },
      { id: 'ae-halal', text: 'Halal certificate for meat/food products' },
      { id: 'ae-label', text: 'Arabic labeling requirements for consumer goods' },
    ],
  },
  {
    code: 'in',
    name: 'India',
    flag: '🇮🇳',
    requirements: [
      { id: 'in-iec', text: 'IEC (Import Export Code) of Indian importer' },
      { id: 'in-gstin', text: 'GSTIN number reference' },
      { id: 'in-bis', text: 'BIS certification for applicable products' },
      { id: 'in-fssai', text: 'FSSAI license for food products' },
    ],
  },
  {
    code: 'cn',
    name: 'China',
    flag: '🇨🇳',
    requirements: [
      { id: 'cn-ccc', text: 'CCC Mark for applicable products', critical: true },
      { id: 'cn-customs', text: 'Chinese customs registration number' },
      { id: 'cn-inspection', text: 'CCIC inspection may be required' },
      { id: 'cn-chinese', text: 'Chinese translations may be required' },
    ],
  },
  {
    code: 'us',
    name: 'United States',
    flag: '🇺🇸',
    requirements: [
      { id: 'us-hts', text: 'HTS Code (10-digit) required' },
      { id: 'us-fda', text: 'FDA registration for food/drug products' },
      { id: 'us-fcc', text: 'FCC certification for electronics' },
      { id: 'us-origin', text: 'Country of origin marking required' },
    ],
  },
  {
    code: 'eu',
    name: 'European Union',
    flag: '🇪🇺',
    requirements: [
      { id: 'eu-ce', text: 'CE Marking for applicable products', critical: true },
      { id: 'eu-eori', text: 'EORI number of EU importer' },
      { id: 'eu-reach', text: 'REACH compliance for chemicals' },
      { id: 'eu-weee', text: 'WEEE registration for electronics' },
    ],
  },
  {
    code: 'sg',
    name: 'Singapore',
    flag: '🇸🇬',
    requirements: [
      { id: 'sg-uen', text: 'UEN (Unique Entity Number) of importer' },
      { id: 'sg-hsa', text: 'HSA approval for health products' },
      { id: 'sg-sfa', text: 'SFA license for food products' },
    ],
  },
];

// PDF Generation (simplified - just opens print dialog)
const generatePDF = () => {
  const printContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>LC Document Preparation Checklist</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
        h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }
        h2 { color: #2d3748; margin-top: 25px; }
        h3 { color: #4a5568; margin-top: 20px; }
        .checklist { list-style: none; padding: 0; }
        .checklist li { padding: 8px 0; border-bottom: 1px dashed #e2e8f0; display: flex; align-items: flex-start; gap: 10px; }
        .checkbox { width: 16px; height: 16px; border: 2px solid #4a5568; border-radius: 3px; flex-shrink: 0; margin-top: 2px; }
        .critical { color: #c53030; font-weight: 600; }
        .tip { font-size: 12px; color: #718096; margin-left: 26px; font-style: italic; }
        .section { margin-bottom: 30px; page-break-inside: avoid; }
        .warning { background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .warning-title { color: #92400e; font-weight: 600; margin-bottom: 10px; }
        @media print { .no-print { display: none; } }
      </style>
    </head>
    <body>
      <h1>📋 LC Document Preparation Checklist</h1>
      <p><strong>Generated:</strong> ${new Date().toLocaleDateString()}</p>
      <p><em>Prepare your documents RIGHT to avoid costly discrepancies. Average discrepancy fee: $50-150 per issue.</em></p>
      
      <div class="section">
        <h2>✅ Before You Start</h2>
        <ul class="checklist">
          ${PRE_UPLOAD_CHECKS.map(item => `
            <li>
              <span class="checkbox"></span>
              <span class="${item.critical ? 'critical' : ''}">${item.text}</span>
            </li>
            ${item.tip ? `<div class="tip">💡 ${item.tip}</div>` : ''}
          `).join('')}
        </ul>
      </div>
      
      ${DOCUMENT_CHECKLISTS.map(doc => `
        <div class="section">
          <h3>${doc.emoji} ${doc.name}</h3>
          <ul class="checklist">
            ${doc.items.map(item => `
              <li>
                <span class="checkbox"></span>
                <span class="${item.critical ? 'critical' : ''}">${item.text}</span>
              </li>
              ${item.tip ? `<div class="tip">💡 ${item.tip}</div>` : ''}
            `).join('')}
          </ul>
        </div>
      `).join('')}
      
      <div class="warning">
        <div class="warning-title">⚠️ Common Mistakes to Avoid</div>
        <ul class="checklist">
          ${COMMON_MISTAKES.map(item => `
            <li>
              <span class="checkbox"></span>
              <span class="${item.critical ? 'critical' : ''}">${item.text}</span>
            </li>
          `).join('')}
        </ul>
      </div>
      
      <div class="section">
        <h2>🌍 Country-Specific Requirements</h2>
        ${COUNTRY_REQUIREMENTS.slice(0, 4).map(country => `
          <h3>${country.flag} ${country.name}</h3>
          <ul class="checklist">
            ${country.requirements.map(item => `
              <li>
                <span class="checkbox"></span>
                <span class="${item.critical ? 'critical' : ''}">${item.text}</span>
              </li>
              ${item.tip ? `<div class="tip">💡 ${item.tip}</div>` : ''}
            `).join('')}
          </ul>
        `).join('')}
      </div>
      
      <div class="section">
        <h2>📤 Upload Tips</h2>
        <ul class="checklist">
          ${UPLOAD_TIPS.map(item => `
            <li>
              <span class="checkbox"></span>
              <span>${item.text}</span>
            </li>
          `).join('')}
        </ul>
      </div>
      
      <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px;">
        Generated by TRDR Hub LCopilot • First-time-right success rate with this guide: 85%+
      </p>
    </body>
    </html>
  `;

  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.print();
  }
};

// Main Component
export function PreparationGuide() {
  const [isOpen, setIsOpen] = useState(false);
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState('quick');

  // Load checked items from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        setCheckedItems(new Set(JSON.parse(saved)));
      }
    } catch (e) {
      console.error('Failed to load checklist state:', e);
    }
  }, []);

  // Save checked items to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...checkedItems]));
    } catch (e) {
      console.error('Failed to save checklist state:', e);
    }
  }, [checkedItems]);

  const toggleItem = (id: string) => {
    setCheckedItems(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Calculate progress
  const totalQuickItems = PRE_UPLOAD_CHECKS.length;
  const checkedQuickItems = PRE_UPLOAD_CHECKS.filter(item => checkedItems.has(item.id)).length;
  const quickProgress = (checkedQuickItems / totalQuickItems) * 100;

  // Render a checklist item
  const renderChecklistItem = (item: ChecklistItem) => (
    <div key={item.id} className="flex items-start gap-3 py-2">
      <Checkbox
        id={item.id}
        checked={checkedItems.has(item.id)}
        onCheckedChange={() => toggleItem(item.id)}
        className="mt-0.5"
      />
      <div className="flex-1 space-y-1">
        <label
          htmlFor={item.id}
          className={cn(
            'text-sm cursor-pointer leading-tight',
            item.critical && 'font-medium text-destructive',
            checkedItems.has(item.id) && 'line-through text-muted-foreground'
          )}
        >
          {item.text}
          {item.critical && !checkedItems.has(item.id) && (
            <Badge variant="destructive" className="ml-2 text-[10px] px-1 py-0">
              Critical
            </Badge>
          )}
        </label>
        {item.tip && (
          <p className="text-xs text-muted-foreground flex items-start gap-1">
            <Lightbulb className="w-3 h-3 mt-0.5 shrink-0 text-amber-500" />
            {item.tip}
          </p>
        )}
      </div>
    </div>
  );

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <Card className="border-exporter/20 bg-gradient-to-br from-exporter/5 to-transparent">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-exporter/5 transition-colors py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-exporter/10 rounded-lg">
                  <BookOpen className="w-5 h-5 text-exporter" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    Document Preparation Guide
                    {quickProgress === 100 && (
                      <Badge variant="outline" className="border-green-500 text-green-600 text-[10px]">
                        <CheckCircle className="w-3 h-3 mr-1" /> Ready
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {isOpen ? 'Checklist to prepare documents before validation' : 'Expand for preparation checklist • First-time-right: 85%+'}
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {!isOpen && quickProgress > 0 && (
                  <div className="flex items-center gap-2">
                    <Progress value={quickProgress} className="w-16 h-1.5" />
                    <span className="text-xs text-muted-foreground">{checkedQuickItems}/{totalQuickItems}</span>
                  </div>
                )}
                {isOpen ? <ChevronUp className="w-5 h-5 text-muted-foreground" /> : <ChevronDown className="w-5 h-5 text-muted-foreground" />}
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="pt-0 pb-4">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <div className="flex items-center justify-between mb-4">
                <TabsList className="grid grid-cols-4 h-8">
                  <TabsTrigger value="quick" className="text-xs px-2">Quick Check</TabsTrigger>
                  <TabsTrigger value="documents" className="text-xs px-2">Documents</TabsTrigger>
                  <TabsTrigger value="countries" className="text-xs px-2">Countries</TabsTrigger>
                  <TabsTrigger value="tips" className="text-xs px-2">Tips</TabsTrigger>
                </TabsList>
                <Button variant="outline" size="sm" onClick={generatePDF} className="h-8 text-xs gap-1.5">
                  <Download className="w-3.5 h-3.5" />
                  Download PDF
                </Button>
              </div>

              {/* Quick Check Tab */}
              <TabsContent value="quick" className="mt-0 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium">Pre-Upload Checklist</h4>
                  <div className="flex items-center gap-2">
                    <Progress value={quickProgress} className="w-24 h-2" />
                    <span className="text-xs text-muted-foreground">{Math.round(quickProgress)}%</span>
                  </div>
                </div>
                <div className="space-y-1 border rounded-lg p-3 bg-background/50">
                  {PRE_UPLOAD_CHECKS.map(renderChecklistItem)}
                </div>
                {quickProgress === 100 && (
                  <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 dark:bg-green-950/30 p-3 rounded-lg">
                    <CheckCircle className="w-4 h-4" />
                    Great! You've completed the quick checklist. Ready to upload!
                  </div>
                )}
              </TabsContent>

              {/* Documents Tab */}
              <TabsContent value="documents" className="mt-0">
                <ScrollArea className="h-[300px] pr-4">
                  <div className="space-y-4">
                    {DOCUMENT_CHECKLISTS.map(doc => (
                      <Collapsible key={doc.id} className="border rounded-lg overflow-hidden">
                        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 hover:bg-muted/50 transition-colors">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{doc.emoji}</span>
                            <span className="font-medium text-sm">{doc.name}</span>
                            <Badge variant="secondary" className="text-[10px]">
                              {doc.items.filter(i => checkedItems.has(i.id)).length}/{doc.items.length}
                            </Badge>
                          </div>
                          <ChevronDown className="w-4 h-4 text-muted-foreground" />
                        </CollapsibleTrigger>
                        <CollapsibleContent className="px-3 pb-3 pt-0 border-t bg-muted/20">
                          {doc.items.map(renderChecklistItem)}
                        </CollapsibleContent>
                      </Collapsible>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>

              {/* Countries Tab */}
              <TabsContent value="countries" className="mt-0">
                <ScrollArea className="h-[300px] pr-4">
                  <div className="grid grid-cols-2 gap-3">
                    {COUNTRY_REQUIREMENTS.map(country => (
                      <Card key={country.code} className="border-dashed">
                        <CardHeader className="py-2 px-3">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <span>{country.flag}</span>
                            {country.name}
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="py-2 px-3 pt-0">
                          <ul className="space-y-1.5 text-xs">
                            {country.requirements.map(req => (
                              <li key={req.id} className="flex items-start gap-1.5">
                                <span className={cn(
                                  "mt-1 w-1.5 h-1.5 rounded-full shrink-0",
                                  req.critical ? "bg-destructive" : "bg-muted-foreground"
                                )} />
                                <span className={req.critical ? 'font-medium' : ''}>{req.text}</span>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>

              {/* Tips Tab */}
              <TabsContent value="tips" className="mt-0 space-y-4">
                {/* Common Mistakes */}
                <div>
                  <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    Common Mistakes to Avoid
                  </h4>
                  <div className="space-y-1 border border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 rounded-lg p-3">
                    {COMMON_MISTAKES.map(item => (
                      <div key={item.id} className="flex items-start gap-2 py-1.5 text-sm">
                        <span className="text-amber-500">✗</span>
                        <span className={item.critical ? 'font-medium' : ''}>{item.text}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Upload Tips */}
                <div>
                  <h4 className="text-sm font-medium flex items-center gap-2 mb-2">
                    <Info className="w-4 h-4 text-blue-500" />
                    Upload Tips
                  </h4>
                  <div className="space-y-1 border border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 rounded-lg p-3">
                    {UPLOAD_TIPS.map(item => (
                      <div key={item.id} className="flex items-start gap-2 py-1.5 text-sm">
                        <span className="text-green-500">✓</span>
                        <span>{item.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Footer */}
            <div className="flex items-center justify-between mt-4 pt-3 border-t text-xs text-muted-foreground">
              <span>Progress saved locally • Resets when you clear browser data</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => setCheckedItems(new Set())}
              >
                Reset Checklist
              </Button>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

export default PreparationGuide;

