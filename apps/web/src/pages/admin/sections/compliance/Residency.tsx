import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Globe } from 'lucide-react';

const mockRegions = [
  { name: 'United States', datacenter: 'us-east-1', customers: 1245, data: '2.4TB', status: 'active' },
  { name: 'European Union', datacenter: 'eu-west-1', customers: 856, data: '1.8TB', status: 'active' },
  { name: 'Asia Pacific', datacenter: 'ap-southeast-1', customers: 423, data: '950GB', status: 'active' },
];

export function ComplianceResidency() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Data Residency</h2>
        <p className="text-muted-foreground">
          Manage data storage locations and regional compliance
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            Regional Data Centers
          </CardTitle>
          <CardDescription>Active data residency regions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockRegions.map((region) => (
              <div key={region.name} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{region.name}</p>
                  <p className="text-sm text-muted-foreground">{region.datacenter} • {region.customers} customers • {region.data} stored</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{region.status}</Badge>
                  <Button variant="outline" size="sm">
                    Configure
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

