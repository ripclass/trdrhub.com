import * as React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Info, Database } from "lucide-react";
import { api } from "@/api/client";

interface EnvironmentInfo {
  environment: string;
  is_production: boolean;
  is_staging: boolean;
  is_development: boolean;
  use_stubs: boolean;
  sample_data_mode: boolean;
}

export function EnvironmentBanner() {
  const [envInfo, setEnvInfo] = React.useState<EnvironmentInfo | null>(null);
  const [isVisible, setIsVisible] = React.useState(true);

  React.useEffect(() => {
    // Fetch environment info from API
    api.get<EnvironmentInfo>("/api/support/environment")
      .then((response) => {
        setEnvInfo(response.data);
        // Only show banner if not production or if sample data mode is enabled
        setIsVisible(!response.data.is_production || response.data.sample_data_mode);
      })
      .catch(() => {
        // Fallback: assume development if API fails
        setEnvInfo({
          environment: "development",
          is_production: false,
          is_staging: false,
          is_development: true,
          use_stubs: false,
          sample_data_mode: false,
        });
        setIsVisible(true);
      });
  }, []);

  if (!isVisible || !envInfo) {
    return null;
  }

  const getEnvironmentLabel = () => {
    if (envInfo.is_production) return "Production";
    if (envInfo.is_staging) return "Staging";
    return "Development";
  };

  const getEnvironmentColor = () => {
    if (envInfo.is_production && !envInfo.sample_data_mode) return "bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-400";
    if (envInfo.is_staging) return "bg-yellow-500/10 border-yellow-500/20 text-yellow-700 dark:text-yellow-400";
    return "bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-400";
  };

  const getEnvironmentIcon = () => {
    if (envInfo.sample_data_mode) return <Database className="h-4 w-4" />;
    if (envInfo.is_staging) return <AlertTriangle className="h-4 w-4" />;
    return <Info className="h-4 w-4" />;
  };

  return (
    <Alert className={`${getEnvironmentColor()} border-t-2 rounded-none sticky top-0 z-50`}>
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2">
          {getEnvironmentIcon()}
          <AlertTitle className="font-semibold">
            {getEnvironmentLabel()}
            {envInfo.sample_data_mode && (
              <Badge variant="outline" className="ml-2 text-xs">
                Sample Data Mode
              </Badge>
            )}
          </AlertTitle>
        </div>
        <AlertDescription className="text-sm">
          {envInfo.sample_data_mode && "You are viewing sample data. Real data is not available."}
          {!envInfo.sample_data_mode && envInfo.is_staging && "This is a staging environment. Data may be reset periodically."}
          {!envInfo.sample_data_mode && envInfo.is_development && "This is a development environment."}
        </AlertDescription>
      </div>
    </Alert>
  );
}

