import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTheme } from "@/providers/ThemeProvider";
import { Moon, Sun, Palette, Table as TableIcon, Type, Layout } from "lucide-react";

export default function ComponentGallery() {
  const { theme, resolvedTheme } = useTheme();

  return (
    <AppShell
      title="Component Gallery"
      subtitle="Professional Bloomberg-style design system components"
      breadcrumbs={[
        { label: "LCopilot", href: "/lcopilot" },
        { label: "Component Gallery" },
      ]}
      compact
    >
      <div className="space-y-8">
        {/* Theme Info */}
        <Card dense>
          <CardHeader dense>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle dense>Current Theme</CardTitle>
                <CardDescription>
                  Theme: <Badge variant="outline">{theme}</Badge> | Resolved: <Badge>{resolvedTheme}</Badge>
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {resolvedTheme === 'dark' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
              </div>
            </div>
          </CardHeader>
          <CardContent dense>
            <p className="text-sm text-muted-foreground">
              This gallery demonstrates the professional, data-dense design system with dark/light theme support.
              All components follow Bloomberg-style conventions for financial data applications.
            </p>
          </CardContent>
        </Card>

        {/* Tabs for Organization */}
        <Tabs defaultValue="buttons" className="w-full">
          <TabsList>
            <TabsTrigger value="buttons">
              <Layout className="w-4 h-4 mr-2" />
              Buttons & Forms
            </TabsTrigger>
            <TabsTrigger value="tables">
              <TableIcon className="w-4 h-4 mr-2" />
              Tables
            </TabsTrigger>
            <TabsTrigger value="typography">
              <Type className="w-4 h-4 mr-2" />
              Typography
            </TabsTrigger>
            <TabsTrigger value="colors">
              <Palette className="w-4 h-4 mr-2" />
              Colors
            </TabsTrigger>
          </TabsList>

          <TabsContent value="buttons" className="space-y-6">
            {/* Buttons */}
            <Card>
              <CardHeader>
                <CardTitle>Buttons</CardTitle>
                <CardDescription>All button variants and sizes</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold mb-3">Variants</h4>
                  <div className="flex flex-wrap gap-2">
                    <Button>Default</Button>
                    <Button variant="secondary">Secondary</Button>
                    <Button variant="outline">Outline</Button>
                    <Button variant="ghost">Ghost</Button>
                    <Button variant="destructive">Destructive</Button>
                    <Button variant="link">Link</Button>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold mb-3">Sizes</h4>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button size="xs">Extra Small</Button>
                    <Button size="sm">Small</Button>
                    <Button size="default">Default</Button>
                    <Button size="lg">Large</Button>
                    <Button size="xl">Extra Large</Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Inputs */}
            <Card>
              <CardHeader>
                <CardTitle>Input Fields</CardTitle>
                <CardDescription>Standard and dense input variants</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Standard Input</label>
                    <Input placeholder="Enter text..." />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Dense Input</label>
                    <Input dense placeholder="Enter text..." />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cards */}
            <Card>
              <CardHeader>
                <CardTitle>Cards</CardTitle>
                <CardDescription>Standard and dense card layouts</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>Standard Card</CardTitle>
                      <CardDescription>Default padding and spacing</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        Content with standard padding for comfortable reading.
                      </p>
                    </CardContent>
                    <CardFooter>
                      <Button size="sm">Action</Button>
                    </CardFooter>
                  </Card>
                  <Card dense>
                    <CardHeader dense>
                      <CardTitle dense>Dense Card</CardTitle>
                      <CardDescription>Compact padding for data density</CardDescription>
                    </CardHeader>
                    <CardContent dense>
                      <p className="text-xs text-muted-foreground">
                        Content with reduced padding for maximum information density.
                      </p>
                    </CardContent>
                    <CardFooter dense>
                      <Button size="xs">Action</Button>
                    </CardFooter>
                  </Card>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tables" className="space-y-6">
            {/* Tables */}
            <Card>
              <CardHeader>
                <CardTitle>Data Tables</CardTitle>
                <CardDescription>Dense tables with sticky headers and numeric alignment</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border">
                  <Table dense sticky>
                    <TableHeader sticky>
                      <TableRow dense>
                        <TableHead dense>Description</TableHead>
                        <TableHead dense>Status</TableHead>
                        <TableHead dense numeric>Amount</TableHead>
                        <TableHead dense numeric>Quantity</TableHead>
                        <TableHead dense numeric>Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody zebra>
                      {Array.from({ length: 10 }).map((_, i) => (
                        <TableRow dense key={i}>
                          <TableCell dense className="font-medium">Transaction {i + 1}</TableCell>
                          <TableCell dense>
                            <Badge variant={i % 3 === 0 ? "default" : i % 2 === 0 ? "secondary" : "outline"}>
                              {i % 3 === 0 ? "Completed" : i % 2 === 0 ? "Pending" : "Processing"}
                            </Badge>
                          </TableCell>
                          <TableCell dense numeric>${(Math.random() * 1000).toFixed(2)}</TableCell>
                          <TableCell dense numeric>{Math.floor(Math.random() * 100)}</TableCell>
                          <TableCell dense numeric className="font-semibold">
                            ${(Math.random() * 10000).toFixed(2)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <p className="text-xs text-muted-foreground mt-3">
                  Features: Dense spacing, sticky header, zebra striping, numeric alignment, right-aligned numbers
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="typography" className="space-y-6">
            {/* Typography */}
            <Card>
              <CardHeader>
                <CardTitle>Typography Scale</CardTitle>
                <CardDescription>Data-dense typography with tight line heights</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <h1>Heading 1 - 18px (text-xl)</h1>
                  <h2>Heading 2 - 16px (text-lg)</h2>
                  <h3>Heading 3 - 14px (text-base)</h3>
                  <h4>Heading 4 - 13px (text-sm)</h4>
                  <p className="text-base">Body text - 14px (text-base)</p>
                  <p className="text-sm">Small text - 13px (text-sm)</p>
                  <p className="text-xs">Extra small - 11px (text-xs)</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="colors" className="space-y-6">
            {/* Colors */}
            <Card>
              <CardHeader>
                <CardTitle>Color Palette</CardTitle>
                <CardDescription>Theme-aware semantic colors</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-background border flex items-center justify-center text-xs">
                      Background
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                      Primary
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-secondary text-secondary-foreground flex items-center justify-center text-xs font-medium">
                      Secondary
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-accent text-accent-foreground flex items-center justify-center text-xs font-medium">
                      Accent
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-success text-success-foreground flex items-center justify-center text-xs font-medium">
                      Success
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-warning text-warning-foreground flex items-center justify-center text-xs font-medium">
                      Warning
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-destructive text-destructive-foreground flex items-center justify-center text-xs font-medium">
                      Destructive
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-20 rounded-md bg-info text-info-foreground flex items-center justify-center text-xs font-medium">
                      Info
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Usage Guidelines */}
        <Card>
          <CardHeader>
            <CardTitle>Usage Guidelines</CardTitle>
            <CardDescription>Best practices for the professional design system</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold mb-2">Data Density</h4>
              <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                <li>Use <code className="text-xs bg-muted px-1 py-0.5 rounded">dense</code> prop on tables for financial data</li>
                <li>Apply <code className="text-xs bg-muted px-1 py-0.5 rounded">numeric</code> prop to TableHead/TableCell for right-aligned numbers</li>
                <li>Enable <code className="text-xs bg-muted px-1 py-0.5 rounded">sticky</code> headers for long tables</li>
                <li>Use <code className="text-xs bg-muted px-1 py-0.5 rounded">zebra</code> prop on TableBody for improved readability</li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-2">Theme Support</h4>
              <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                <li>All components automatically adapt to light/dark theme</li>
                <li>Use semantic color tokens (primary, secondary, accent, etc.)</li>
                <li>Charts use theme-aware colors via getChartTheme()</li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-2">Accessibility</h4>
              <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                <li>High-contrast focus rings on all interactive elements</li>
                <li>Proper ARIA labels on form controls</li>
                <li>Keyboard navigation support for tables and filters</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

