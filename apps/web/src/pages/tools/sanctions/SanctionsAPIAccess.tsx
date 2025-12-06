import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import {
  Key,
  Plus,
  Copy,
  Trash2,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  Code,
  Zap,
  Globe,
} from "lucide-react";

interface APIKey {
  key_id: string;
  name: string;
  created_at: string;
  last_used?: string;
  permissions: string[];
  is_active: boolean;
}

const sampleKeys: APIKey[] = [
  {
    key_id: "sk_live_abc123...def456",
    name: "Production ERP",
    created_at: "2025-12-01T10:00:00Z",
    last_used: "2025-12-06T18:30:00Z",
    permissions: ["screen:party", "screen:vessel", "batch:upload"],
    is_active: true,
  },
  {
    key_id: "sk_test_xyz789...ghi012",
    name: "Development",
    created_at: "2025-11-15T09:00:00Z",
    permissions: ["screen:party"],
    is_active: true,
  },
];

export default function SanctionsAPIAccess() {
  const { toast } = useToast();
  const [keys, setKeys] = useState<APIKey[]>(sampleKeys);
  const [newKeyName, setNewKeyName] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);

  const handleCreateKey = () => {
    if (!newKeyName.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a name for your API key",
        variant: "destructive",
      });
      return;
    }

    const fullKey = `sk_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
    
    const newKey: APIKey = {
      key_id: fullKey.substring(0, 15) + "..." + fullKey.substring(fullKey.length - 6),
      name: newKeyName,
      created_at: new Date().toISOString(),
      permissions: ["screen:party", "screen:vessel", "screen:goods", "batch:upload"],
      is_active: true,
    };

    setKeys([newKey, ...keys]);
    setNewlyCreatedKey(fullKey);
    setNewKeyName("");
    setIsCreateDialogOpen(false);
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toast({
      title: "Copied!",
      description: "API key copied to clipboard",
    });
  };

  const handleDeleteKey = (keyId: string) => {
    setKeys(keys.filter(k => k.key_id !== keyId));
    toast({
      title: "Key revoked",
      description: "API key has been permanently revoked",
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Key className="w-6 h-6 text-red-400" />
            API Access
          </h1>
          <p className="text-slate-400 mt-1">
            Programmatic access for ERP and compliance system integration
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-red-500 hover:bg-red-600 text-white">
              <Plus className="w-4 h-4 mr-2" />
              Create API Key
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-slate-900 border-slate-800">
            <DialogHeader>
              <DialogTitle className="text-white">Create API Key</DialogTitle>
              <DialogDescription className="text-slate-400">
                Generate a new API key for programmatic access
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label className="text-white">Key Name</Label>
                <Input
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g., Production ERP, Development"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <p className="text-sm text-amber-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  The API key will only be shown once. Store it securely.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => setIsCreateDialogOpen(false)}
                className="border-slate-700 text-slate-400"
              >
                Cancel
              </Button>
              <Button onClick={handleCreateKey} className="bg-red-500 hover:bg-red-600">
                Create Key
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Newly Created Key */}
      {newlyCreatedKey && (
        <Card className="bg-emerald-500/10 border-emerald-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium text-white">API Key Created</p>
                  <p className="text-sm text-slate-400">Copy it now - you won't see it again</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <code className="px-3 py-2 bg-slate-800 rounded text-sm text-white font-mono">
                  {showKey ? newlyCreatedKey : "••••••••••••••••••••••••••••"}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowKey(!showKey)}
                  className="text-slate-400 hover:text-white"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleCopyKey(newlyCreatedKey)}
                  className="text-slate-400 hover:text-white"
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Keys List */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Your API Keys</CardTitle>
          <CardDescription className="text-slate-400">
            Manage keys for programmatic access to the screening API
          </CardDescription>
        </CardHeader>
        <CardContent>
          {keys.length === 0 ? (
            <div className="text-center py-8">
              <Key className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No API keys</h3>
              <p className="text-slate-400">Create an API key to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              {keys.map((key) => (
                <div
                  key={key.key_id}
                  className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
                      <Key className="w-5 h-5 text-red-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">{key.name}</span>
                        {key.is_active ? (
                          <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">Active</Badge>
                        ) : (
                          <Badge className="bg-slate-500/20 text-slate-400 text-xs">Inactive</Badge>
                        )}
                      </div>
                      <code className="text-sm text-slate-500 font-mono">{key.key_id}</code>
                      <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                        <span>Created: {new Date(key.created_at).toLocaleDateString()}</span>
                        {key.last_used && (
                          <span>Last used: {new Date(key.last_used).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteKey(key.key_id)}
                    className="text-slate-500 hover:text-red-400"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Usage Stats */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            API Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-slate-800/50 rounded-lg text-center">
              <p className="text-3xl font-bold text-white">0</p>
              <p className="text-sm text-slate-400">Requests this month</p>
            </div>
            <div className="p-4 bg-slate-800/50 rounded-lg text-center">
              <p className="text-3xl font-bold text-white">10,000</p>
              <p className="text-sm text-slate-400">Monthly limit</p>
            </div>
            <div className="p-4 bg-slate-800/50 rounded-lg text-center">
              <p className="text-3xl font-bold text-emerald-400">100%</p>
              <p className="text-sm text-slate-400">Available</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Start Guide */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Code className="w-5 h-5 text-red-400" />
            Quick Start
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-slate-950 rounded-lg font-mono text-sm">
            <p className="text-slate-500"># Screen a party</p>
            <p className="text-white">
              curl -X POST https://api.trdrhub.com/sanctions/screen/party \
            </p>
            <p className="text-white pl-4">
              -H "Authorization: Bearer YOUR_API_KEY" \
            </p>
            <p className="text-white pl-4">
              -H "Content-Type: application/json" \
            </p>
            <p className="text-white pl-4">
              -d '{`{"name": "Acme Trading Co", "country": "US"}`}'
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <h4 className="font-medium text-white mb-1">Authentication</h4>
              <p className="text-slate-400">Pass API key in Authorization header as Bearer token</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <h4 className="font-medium text-white mb-1">Rate Limits</h4>
              <p className="text-slate-400">1,000 requests/hour per key. Contact us for higher limits.</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <h4 className="font-medium text-white mb-1">Documentation</h4>
              <p className="text-slate-400">Full API docs at /api/docs</p>
            </div>
          </div>

          <Button variant="outline" className="border-slate-700 text-slate-400 hover:text-white" asChild>
            <a href="/api/docs" target="_blank">
              <Globe className="w-4 h-4 mr-2" />
              View Full API Documentation
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

