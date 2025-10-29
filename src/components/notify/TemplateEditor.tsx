import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, FileText, Code, Info } from 'lucide-react';

interface TemplateEditorProps {
  template?: any;
  onSave: (templateData: any) => void;
  onClose: () => void;
}

const TemplateEditor: React.FC<TemplateEditorProps> = ({ template, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    template_key: '',
    locale: 'en',
    subject_template: '',
    body_template: '',
    description: '',
    active: true
  });

  const [previewContext, setPreviewContext] = useState({
    tenant: 'demo',
    bank: 'test-bank',
    timestamp: new Date().toISOString(),
    event: {
      event_type: 'collab.thread.created',
      context: {
        thread_id: 'thread_123',
        title: 'Document Discrepancy Found',
        priority: 'high'
      }
    }
  });

  const [renderedPreview, setRenderedPreview] = useState({ subject: '', body: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const eventTypes = [
    'collab.thread.created',
    'collab.comment.created',
    'collab.mention.created',
    'bulk.job.completed',
    'bulk.job.failed',
    'workflow.override.updated',
    'discrepancy.high',
    'discrepancy.escalation'
  ];

  useEffect(() => {
    if (template) {
      setFormData({
        template_key: template.template_key || '',
        locale: template.locale || 'en',
        subject_template: template.subject_template || '',
        body_template: template.body_template || '',
        description: template.description || '',
        active: template.active !== false
      });
    }
  }, [template]);

  useEffect(() => {
    renderPreview();
  }, [formData.subject_template, formData.body_template, previewContext]);

  const renderPreview = async () => {
    if (!formData.template_key || (!formData.subject_template && !formData.body_template)) {
      setRenderedPreview({ subject: '', body: '' });
      return;
    }

    try {
      const response = await fetch(`/api/notifications/templates/${formData.template_key}/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: previewContext })
      });

      if (response.ok) {
        const preview = await response.json();
        setRenderedPreview(preview);
      }
    } catch (error) {
      console.error('Failed to render preview:', error);
      // Fallback to simple string replacement
      const subject = replaceVariables(formData.subject_template, previewContext);
      const body = replaceVariables(formData.body_template, previewContext);
      setRenderedPreview({ subject, body });
    }
  };

  const replaceVariables = (template: string, context: any) => {
    let result = template;
    const flatten = (obj: any, prefix = '') => {
      const flattened: any = {};
      for (const key in obj) {
        if (typeof obj[key] === 'object' && obj[key] !== null) {
          Object.assign(flattened, flatten(obj[key], prefix + key + '.'));
        } else {
          flattened[prefix + key] = obj[key];
        }
      }
      return flattened;
    };

    const flatContext = flatten(context);
    for (const [key, value] of Object.entries(flatContext)) {
      const placeholder = `{${key}}`;
      result = result.replace(new RegExp(placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), String(value));
    }

    return result;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await onSave(formData);
    } catch (error) {
      console.error('Failed to save template:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getTemplateHelp = () => (
    <Alert>
      <Info className="h-4 w-4" />
      <AlertDescription>
        <div className="space-y-2">
          <p><strong>Available variables:</strong></p>
          <ul className="text-sm space-y-1">
            <li><code>{'{tenant}'}</code> - Tenant name</li>
            <li><code>{'{bank}'}</code> - Bank alias</li>
            <li><code>{'{timestamp}'}</code> - Event timestamp</li>
            <li><code>{'{event.event_type}'}</code> - Event type</li>
            <li><code>{'{event.context.*}'}</code> - Event-specific data</li>
          </ul>
          <p className="text-sm mt-2">
            Use Markdown formatting: **bold**, *italic*, `code`, [link](url)
          </p>
        </div>
      </AlertDescription>
    </Alert>
  );

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5" />
            <span>{template ? 'Edit Template' : 'Add Template'}</span>
          </DialogTitle>
          <DialogDescription>
            Create and customize notification templates with variables and Markdown
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <Tabs defaultValue="editor" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="editor">Template Editor</TabsTrigger>
              <TabsTrigger value="preview">Live Preview</TabsTrigger>
            </TabsList>

            <TabsContent value="editor" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Template Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="template_key">Template Key *</Label>
                      <Select
                        value={formData.template_key}
                        onValueChange={(value) => setFormData({ ...formData, template_key: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select event type" />
                        </SelectTrigger>
                        <SelectContent>
                          {eventTypes.map((eventType) => (
                            <SelectItem key={eventType} value={eventType}>
                              {eventType.replace(/\./g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="locale">Locale</Label>
                      <Select
                        value={formData.locale}
                        onValueChange={(value) => setFormData({ ...formData, locale: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">English</SelectItem>
                          <SelectItem value="es">Spanish</SelectItem>
                          <SelectItem value="fr">French</SelectItem>
                          <SelectItem value="zh">Chinese</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Template description..."
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="active"
                      checked={formData.active}
                      onCheckedChange={(checked) => setFormData({ ...formData, active: checked })}
                    />
                    <Label htmlFor="active">Template Active</Label>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Template Content</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="subject_template">Subject Template *</Label>
                    <Input
                      id="subject_template"
                      value={formData.subject_template}
                      onChange={(e) => setFormData({ ...formData, subject_template: e.target.value })}
                      placeholder="New {event.event_type} in {tenant}"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="body_template">Body Template *</Label>
                    <Textarea
                      id="body_template"
                      value={formData.body_template}
                      onChange={(e) => setFormData({ ...formData, body_template: e.target.value })}
                      placeholder={`Hello,

A new {event.event_type} has occurred in **{tenant}**.

**Details:**
- Timestamp: {timestamp}
- Event ID: {event.context.thread_id}
- Priority: {event.context.priority}

Please review and take appropriate action.

Best regards,
LCopilot Team`}
                      rows={12}
                      required
                    />
                  </div>

                  {getTemplateHelp()}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="preview" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center space-x-2">
                    <Eye className="h-5 w-5" />
                    <span>Live Preview</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Preview Context (modify to test different scenarios)</Label>
                    <Textarea
                      value={JSON.stringify(previewContext, null, 2)}
                      onChange={(e) => {
                        try {
                          const context = JSON.parse(e.target.value);
                          setPreviewContext(context);
                        } catch {
                          // Invalid JSON, ignore
                        }
                      }}
                      rows={8}
                      className="font-mono text-sm"
                    />
                  </div>

                  <div className="border rounded-lg p-4 bg-gray-50">
                    <h4 className="font-semibold mb-2">Rendered Output:</h4>

                    {renderedPreview.subject && (
                      <div className="mb-4">
                        <Label className="text-sm font-medium">Subject:</Label>
                        <div className="p-2 bg-white border rounded mt-1">
                          {renderedPreview.subject}
                        </div>
                      </div>
                    )}

                    {renderedPreview.body && (
                      <div>
                        <Label className="text-sm font-medium">Body:</Label>
                        <div className="p-4 bg-white border rounded mt-1 whitespace-pre-wrap">
                          {renderedPreview.body}
                        </div>
                      </div>
                    )}

                    {!renderedPreview.subject && !renderedPreview.body && (
                      <p className="text-gray-500 italic">Enter template content to see preview</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center space-x-2">
                    <Code className="h-5 w-5" />
                    <span>Quick Test</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-2">
                    {eventTypes.slice(0, 6).map((eventType) => (
                      <Button
                        key={eventType}
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setPreviewContext({
                            ...previewContext,
                            event: {
                              event_type: eventType,
                              context: {
                                thread_id: 'test_123',
                                title: 'Test Event',
                                priority: 'normal'
                              }
                            }
                          });
                        }}
                      >
                        {eventType.split('.').pop()}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          <div className="flex justify-end space-x-3 pt-6 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Template'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export { TemplateEditor };