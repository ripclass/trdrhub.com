/**
 * In-app Tutorials Component
 * Provides interactive tutorials and keyboard shortcuts guide
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Keyboard,
  BookOpen,
  PlayCircle,
  X,
  Command,
  ArrowRight,
  Clock,
} from "lucide-react";

interface Tutorial {
  id: string;
  title: string;
  description: string;
  steps: TutorialStep[];
  estimatedTime: string;
}

interface TutorialStep {
  title: string;
  description: string;
  action?: string; // Optional action to highlight
}

interface KeyboardShortcut {
  keys: string[];
  description: string;
  category: 'navigation' | 'actions' | 'filters' | 'general';
}

const TUTORIALS: Tutorial[] = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    description: 'Learn the basics of navigating and using LCopilot',
    estimatedTime: '5 min',
    steps: [
      {
        title: 'Welcome to LCopilot',
        description: 'LCopilot helps you validate Letter of Credit documents efficiently.',
      },
      {
        title: 'Dashboard Overview',
        description: 'Your dashboard shows recent validations, statistics, and quick actions.',
      },
      {
        title: 'Upload Documents',
        description: 'Click "Upload" in the sidebar to start validating LC documents.',
      },
      {
        title: 'View Results',
        description: 'Check validation results in the "Results" tab to see compliance scores and discrepancies.',
      },
    ],
  },
  {
    id: 'bank-workflow',
    title: 'Bank Workflow',
    description: 'Master the bank approval and discrepancy workflow',
    estimatedTime: '10 min',
    steps: [
      {
        title: 'Queue Operations',
        description: 'Monitor and manage validation jobs in the processing queue.',
        action: 'Navigate to Queue tab',
      },
      {
        title: 'Review Results',
        description: 'Review validation results and identify discrepancies.',
        action: 'Open Results tab',
      },
      {
        title: 'Assign Discrepancies',
        description: 'Assign discrepancies to team members with due dates.',
        action: 'Go to Discrepancies tab',
      },
      {
        title: 'Approve or Reject',
        description: 'Use the Approvals tab to approve or reject LC validations.',
        action: 'Open Approvals tab',
      },
    ],
  },
  {
    id: 'saved-views',
    title: 'Saved Views & Filters',
    description: 'Save and reuse filter combinations',
    estimatedTime: '3 min',
    steps: [
      {
        title: 'Apply Filters',
        description: 'Set up your desired filters (status, date range, client, etc.).',
      },
      {
        title: 'Save View',
        description: 'Click "Save View" button to save your current filter combination.',
      },
      {
        title: 'Load View',
        description: 'Select a saved view from the dropdown to quickly apply filters.',
      },
      {
        title: 'Share Views',
        description: 'Share saved views with your team for consistent filtering.',
      },
    ],
  },
];

const KEYBOARD_SHORTCUTS: KeyboardShortcut[] = [
  // Navigation
  { keys: ['G', 'D'], description: 'Go to Dashboard', category: 'navigation' },
  { keys: ['G', 'U'], description: 'Go to Upload', category: 'navigation' },
  { keys: ['G', 'R'], description: 'Go to Results', category: 'navigation' },
  { keys: ['G', 'A'], description: 'Go to Analytics', category: 'navigation' },
  
  // Actions
  { keys: ['Ctrl', 'K'], description: 'Open command palette', category: 'actions' },
  { keys: ['Ctrl', 'S'], description: 'Save current view', category: 'actions' },
  { keys: ['Ctrl', 'E'], description: 'Export results', category: 'actions' },
  
  // Filters
  { keys: ['/', '/'], description: 'Focus search', category: 'filters' },
  { keys: ['Esc'], description: 'Clear filters', category: 'filters' },
  
  // General
  { keys: ['?'], description: 'Show keyboard shortcuts', category: 'general' },
  { keys: ['Ctrl', '?'], description: 'Open help', category: 'general' },
];

export function InAppTutorials({ dashboard }: { dashboard: 'bank' | 'exporter' | 'importer' }) {
  const { toast } = useToast();
  const [open, setOpen] = React.useState(false);
  const [activeTutorial, setActiveTutorial] = React.useState<string | null>(null);

  // Keyboard shortcut handler
  React.useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Show shortcuts on '?' key
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        setOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  const handleStartTutorial = (tutorialId: string) => {
    setActiveTutorial(tutorialId);
    toast({
      title: 'Tutorial Started',
      description: 'Follow the steps to complete the tutorial.',
    });
  };

  const shortcutsByCategory = React.useMemo(() => {
    const grouped: Record<string, KeyboardShortcut[]> = {};
    KEYBOARD_SHORTCUTS.forEach((shortcut) => {
      if (!grouped[shortcut.category]) {
        grouped[shortcut.category] = [];
      }
      grouped[shortcut.category].push(shortcut);
    });
    return grouped;
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <BookOpen className="h-4 w-4" />
          <span className="hidden md:inline">Tutorials</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Tutorials & Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Learn how to use LCopilot efficiently with interactive tutorials and keyboard shortcuts.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="tutorials" className="w-full">
          <TabsList>
            <TabsTrigger value="tutorials">Tutorials</TabsTrigger>
            <TabsTrigger value="shortcuts">Keyboard Shortcuts</TabsTrigger>
          </TabsList>

          <TabsContent value="tutorials" className="space-y-4 mt-4">
            <div className="grid gap-4">
              {TUTORIALS.map((tutorial) => (
                <div
                  key={tutorial.id}
                  className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold mb-1">{tutorial.title}</h3>
                      <p className="text-sm text-muted-foreground mb-3">
                        {tutorial.description}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{tutorial.estimatedTime}</span>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStartTutorial(tutorial.id)}
                    >
                      <PlayCircle className="h-4 w-4 mr-2" />
                      Start
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="shortcuts" className="space-y-4 mt-4">
            {Object.entries(shortcutsByCategory).map(([category, shortcuts]) => (
              <div key={category}>
                <h3 className="font-semibold mb-2 capitalize">{category}</h3>
                <div className="space-y-2">
                  {shortcuts.map((shortcut, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 rounded hover:bg-muted/50"
                    >
                      <span className="text-sm">{shortcut.description}</span>
                      <div className="flex items-center gap-1">
                        {shortcut.keys.map((key, keyIdx) => (
                          <React.Fragment key={keyIdx}>
                            <Badge variant="outline" className="font-mono text-xs">
                              {key === 'Ctrl' ? (navigator.platform.includes('Mac') ? '⌘' : 'Ctrl') : key}
                            </Badge>
                            {keyIdx < shortcut.keys.length - 1 && (
                              <span className="text-muted-foreground mx-1">+</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

