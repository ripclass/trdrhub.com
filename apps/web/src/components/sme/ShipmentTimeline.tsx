/**
 * Shipment Timeline Component for SME Dashboards
 * Track shipment milestones with reminders and notifications
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
  Bell,
  BellOff,
  Edit,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { format, isPast, isToday, isFuture, addDays } from "date-fns";

interface Milestone {
  id: string;
  lcNumber: string;
  title: string;
  description?: string;
  dueDate: string; // ISO date string
  status: "pending" | "completed" | "overdue";
  reminderEnabled: boolean;
  reminderDaysBefore: number;
  completedAt?: string;
  notes?: string;
}

interface ShipmentTimelineProps {
  embedded?: boolean;
  lcNumber?: string;
}

const STORAGE_KEY = "lcopilot_shipment_timelines";

// Mock milestones - replace with API calls
const mockMilestones: Milestone[] = [
  {
    id: "milestone-1",
    lcNumber: "LC-2024-001",
    title: "Shipment Date",
    description: "Latest date of shipment as per LC",
    dueDate: addDays(new Date(), 5).toISOString(),
    status: "pending",
    reminderEnabled: true,
    reminderDaysBefore: 3,
  },
  {
    id: "milestone-2",
    lcNumber: "LC-2024-001",
    title: "Document Presentation",
    description: "Present documents to bank within 21 days of shipment",
    dueDate: addDays(new Date(), 26).toISOString(),
    status: "pending",
    reminderEnabled: true,
    reminderDaysBefore: 7,
  },
  {
    id: "milestone-3",
    lcNumber: "LC-2024-002",
    title: "LC Expiry",
    description: "Letter of Credit expires",
    dueDate: addDays(new Date(), -2).toISOString(),
    status: "overdue",
    reminderEnabled: true,
    reminderDaysBefore: 14,
  },
];

export function ShipmentTimeline({ embedded = false, lcNumber }: ShipmentTimelineProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [milestones, setMilestones] = React.useState<Milestone[]>(mockMilestones);
  const [showAddDialog, setShowAddDialog] = React.useState(false);
  const [editingMilestone, setEditingMilestone] = React.useState<Milestone | null>(null);
  
  // Add/Edit form state
  const [formTitle, setFormTitle] = React.useState("");
  const [formDescription, setFormDescription] = React.useState("");
  const [formDueDate, setFormDueDate] = React.useState("");
  const [formReminderEnabled, setFormReminderEnabled] = React.useState(true);
  const [formReminderDays, setFormReminderDays] = React.useState(7);

  // Load milestones from localStorage
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const storedMilestones: Milestone[] = JSON.parse(stored);
        setMilestones([...mockMilestones, ...storedMilestones]);
      }
    } catch (error) {
      console.error("Failed to load shipment timelines:", error);
    }
  }, []);

  // Filter by LC number if provided
  const filteredMilestones = React.useMemo(() => {
    let filtered = milestones;
    if (lcNumber) {
      filtered = filtered.filter((m) => m.lcNumber === lcNumber);
    }
    // Sort by due date
    return filtered.sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());
  }, [milestones, lcNumber]);

  // Check for upcoming reminders
  React.useEffect(() => {
    const now = new Date();
    filteredMilestones.forEach((milestone) => {
      if (milestone.reminderEnabled && milestone.status === "pending") {
        const dueDate = new Date(milestone.dueDate);
        const reminderDate = addDays(dueDate, -milestone.reminderDaysBefore);
        
        if (isToday(reminderDate) || (isPast(reminderDate) && isFuture(dueDate))) {
          // Show reminder notification
          toast({
            title: "Milestone Reminder",
            description: `${milestone.title} for ${milestone.lcNumber} is due in ${milestone.reminderDaysBefore} days.`,
          });
        }
      }
    });
  }, [filteredMilestones, toast]);

  const handleAddMilestone = () => {
    if (!formTitle.trim() || !formDueDate) {
      toast({
        title: "Fields Required",
        description: "Please provide title and due date.",
        variant: "destructive",
      });
      return;
    }

    const newMilestone: Milestone = {
      id: `milestone-${Date.now()}`,
      lcNumber: lcNumber || "LC-XXXX-XXXX",
      title: formTitle.trim(),
      description: formDescription.trim() || undefined,
      dueDate: new Date(formDueDate).toISOString(),
      status: isPast(new Date(formDueDate)) ? "overdue" : "pending",
      reminderEnabled: formReminderEnabled,
      reminderDaysBefore: formReminderDays,
    };

    const updated = [...milestones, newMilestone];
    setMilestones(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((m) => !mockMilestones.find((mock) => mock.id === m.id))));

    // Reset form
    setFormTitle("");
    setFormDescription("");
    setFormDueDate("");
    setFormReminderEnabled(true);
    setFormReminderDays(7);
    setShowAddDialog(false);

    toast({
      title: "Milestone Added",
      description: "New milestone has been added to your timeline.",
    });
  };

  const handleComplete = (id: string) => {
    const updated = milestones.map((m) =>
      m.id === id
        ? { ...m, status: "completed" as const, completedAt: new Date().toISOString() }
        : m
    );
    setMilestones(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((m) => !mockMilestones.find((mock) => mock.id === m.id))));
    
    toast({
      title: "Milestone Completed",
      description: "Milestone marked as completed.",
    });
  };

  const handleToggleReminder = (id: string) => {
    const updated = milestones.map((m) =>
      m.id === id ? { ...m, reminderEnabled: !m.reminderEnabled } : m
    );
    setMilestones(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((m) => !mockMilestones.find((mock) => mock.id === m.id))));
  };

  const handleDelete = (id: string) => {
    if (confirm("Delete this milestone?")) {
      const updated = milestones.filter((m) => m.id !== id);
      setMilestones(updated);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((m) => !mockMilestones.find((mock) => mock.id === m.id))));
      
      toast({
        title: "Milestone Deleted",
        description: "Milestone has been removed.",
      });
    }
  };

  const getStatusBadge = (milestone: Milestone) => {
    const dueDate = new Date(milestone.dueDate);
    let status = milestone.status;
    
    // Update status based on date
    if (status === "pending" && isPast(dueDate)) {
      status = "overdue";
    }

    switch (status) {
      case "completed":
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" /> Completed</Badge>;
      case "overdue":
        return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" /> Overdue</Badge>;
      case "pending":
        if (isToday(dueDate)) {
          return <Badge className="bg-yellow-500">Due Today</Badge>;
        } else if (isFuture(dueDate)) {
          const daysUntil = Math.ceil((dueDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
          return <Badge variant="secondary">{daysUntil} days left</Badge>;
        }
        return <Badge variant="secondary">Pending</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Shipment Timeline</h2>
          <p className="text-muted-foreground">
            Track important milestones and get reminders for your LC shipments.
          </p>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Milestones</CardTitle>
              <CardDescription>
                {filteredMilestones.length} milestone{filteredMilestones.length !== 1 ? 's' : ''} tracked
              </CardDescription>
            </div>
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Milestone
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Milestone</DialogTitle>
                  <DialogDescription>
                    Create a new milestone to track important dates in your shipment timeline.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label htmlFor="milestone-title">Title *</Label>
                    <Input
                      id="milestone-title"
                      placeholder="e.g., Shipment Date, Document Presentation"
                      value={formTitle}
                      onChange={(e) => setFormTitle(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="milestone-description">Description</Label>
                    <Input
                      id="milestone-description"
                      placeholder="Optional description"
                      value={formDescription}
                      onChange={(e) => setFormDescription(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="milestone-date">Due Date *</Label>
                    <Input
                      id="milestone-date"
                      type="date"
                      value={formDueDate}
                      onChange={(e) => setFormDueDate(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="reminder-enabled"
                      checked={formReminderEnabled}
                      onChange={(e) => setFormReminderEnabled(e.target.checked)}
                      className="rounded"
                    />
                    <Label htmlFor="reminder-enabled" className="cursor-pointer">
                      Enable reminder
                    </Label>
                  </div>
                  {formReminderEnabled && (
                    <div>
                      <Label htmlFor="reminder-days">Remind me (days before)</Label>
                      <Select
                        value={formReminderDays.toString()}
                        onValueChange={(value) => setFormReminderDays(parseInt(value))}
                      >
                        <SelectTrigger id="reminder-days">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">1 day before</SelectItem>
                          <SelectItem value="3">3 days before</SelectItem>
                          <SelectItem value="7">7 days before</SelectItem>
                          <SelectItem value="14">14 days before</SelectItem>
                          <SelectItem value="30">30 days before</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleAddMilestone} disabled={!formTitle.trim() || !formDueDate}>
                    Add Milestone
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {filteredMilestones.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No milestones tracked</p>
              <p className="text-sm text-muted-foreground mt-2">
                Add milestones to track important dates in your shipment timeline
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredMilestones.map((milestone) => {
                const dueDate = new Date(milestone.dueDate);
                const isOverdue = milestone.status === "overdue" || (milestone.status === "pending" && isPast(dueDate));
                
                return (
                  <Card key={milestone.id} className={isOverdue ? "border-destructive" : ""}>
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold">{milestone.title}</h3>
                            {getStatusBadge(milestone)}
                          </div>
                          {milestone.description && (
                            <p className="text-sm text-muted-foreground mb-2">
                              {milestone.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Calendar className="h-4 w-4" />
                              <span>{format(dueDate, "MMM dd, yyyy")}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="h-4 w-4" />
                              <span>LC: {milestone.lcNumber}</span>
                            </div>
                            {milestone.reminderEnabled && (
                              <div className="flex items-center gap-1">
                                <Bell className="h-4 w-4" />
                                <span>{milestone.reminderDaysBefore} days before</span>
                              </div>
                            )}
                          </div>
                          {milestone.completedAt && (
                            <p className="text-xs text-muted-foreground mt-2">
                              Completed: {format(new Date(milestone.completedAt), "MMM dd, yyyy")}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {milestone.status !== "completed" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleComplete(milestone.id)}
                            >
                              <CheckCircle2 className="h-4 w-4 mr-2" />
                              Complete
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleReminder(milestone.id)}
                          >
                            {milestone.reminderEnabled ? (
                              <Bell className="h-4 w-4" />
                            ) : (
                              <BellOff className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(milestone.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

